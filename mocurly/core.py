import recurly
import re
import ssl
import xml.dom.minidom as minidom
from six.moves.urllib.parse import urlparse, parse_qs
from httpretty import HTTPretty
from jinja2 import Environment, PackageLoader
jinja2_env = Environment(loader=PackageLoader('mocurly', 'templates'), extensions=['jinja2.ext.with_'])

from .errors import ResponseError
from .backend import clear_backends

def details_route(method, uri, is_list=False):
    def details_route_decorator(func):
        func.is_route = True
        func.method = method
        func.uri = uri
        func.is_list = is_list
        return func
    return details_route_decorator

class callback(object):
    def __init__(self, mocurly_instance):
        self.mocurly_instance = mocurly_instance

    def __call__(self, func):
        def wrapped(request, uri, headers, **kwargs):
            # If we want to timeout the request, timeout, but only if we aren't
            # going to allow the POST
            if (self.mocurly_instance.should_timeout(request) and
                not self.mocurly_instance.should_timeout_successful_post(request)):
                raise ssl.SSLError('The read operation timed out')

            try:
                return_val = func(request, uri, headers, **kwargs)
            except ResponseError as exc:
                if not self.mocurly_instance.should_timeout_successful_post(request):
                    return exc.status_code, headers, exc.response_body

            if self.mocurly_instance.should_timeout_successful_post(request):
                raise ssl.SSLError('The read operation timed out')

            return return_val
        return wrapped

def serialize_list(template, object_type_plural, object_type, object_list):
    serialized_obj_list = []
    for obj in object_list:
        serialized_obj_list.append(serialize(template, object_type, obj))
    return '<{0} type="array">{1}</{0}>'.format(object_type_plural, ''.join(serialized_obj_list)), len(serialized_obj_list)

def serialize(template, object_type, object_dict):
    # Takes in the object type + dictionary representation and returns the XML
    template = jinja2_env.get_template(template)
    kwargs = {}
    kwargs[object_type] = object_dict
    return template.render(**kwargs)

def deserialize(xml):
    # Takes in XML and returns: object type + dictionary representation
    parsed_xml = minidom.parseString(xml)
    assert len(parsed_xml.childNodes) == 1 # only know of xml input with 1 child node, since thats all there is to recurly
    root = parsed_xml.firstChild
    if root.hasAttribute('type') and root.getAttribute('type') == 'array':
        return _deserialize_list(root)
    else:
        return _deserialize_item(root)

def _deserialize_list(root):
    return [_deserialize_item(node)[1] for node in root.childNodes]

def _deserialize_item(root):
    object_type = root.tagName
    obj = {}
    for node in root.childNodes:
        if node.hasAttribute('nil'):
            obj[node.tagName] = None
        elif len(node.childNodes) == 1 and node.childNodes[0].nodeType == minidom.Node.TEXT_NODE:
            obj[node.tagName] = node.firstChild.nodeValue
        elif node.hasAttribute('type') and node.getAttribute('type') == 'array':
            obj[node.tagName] = _deserialize_list(node)
        else:
            child_object_type, child_object = _deserialize_item(node)
            obj[node.tagName] = child_object
    return object_type, obj

class mocurly(object):
    def __init__(self, func=None):
        self.started = False
        HTTPretty.reset()

        self.timeout_filter = None
        self.timeout_connection = False
        self.timeout_connection_successful_post = False
        self.func = func

    def __call__(self, *args, **kwargs):
        self.start()
        try:
            retval = self.func(*args, **kwargs)
        finally:
            self.stop()
        return retval

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, tb):
        self.stop()

    def start(self):
        from .endpoints import clear_endpoints
        self.started = True
        clear_endpoints()
        clear_backends()

        if not HTTPretty.is_enabled():
            HTTPretty.enable()

        self._register()

    def stop(self):
        if not self.started:
            raise RuntimeError('Called stop() before start()')

        HTTPretty.disable()

    def start_timeout(self, timeout_filter=None):
        self.timeout_filter = timeout_filter
        self.timeout_connection = True

    def should_timeout(self, request):
        if self.timeout_filter is None or self.timeout_filter(request):
            return self.timeout_connection
        return False

    def stop_timeout(self):
        self.timeout_filter = None
        self.timeout_connection = False

    def start_timeout_successful_post(self, timeout_filter=None):
        self.timeout_filter = timeout_filter
        self.timeout_connection_successful_post = True

    def should_timeout_successful_post(self, request):
        # only applies to POST requests
        if request.method != 'POST':
            return False
        if self.timeout_filter is None or self.timeout_filter(request):
            return self.timeout_connection_successful_post
        return False

    def stop_timeout_successful_post(self):
        self.timeout_filter = None
        self.timeout_connection_successful_post = False

    def register_transaction_failure(self, account_code, error_code):
        from .endpoints import transactions_endpoint
        transactions_endpoint.register_transaction_failure(account_code, error_code)

    def _register(self):
        from .endpoints import endpoints
        for endpoint in endpoints:
            # register list views
            list_uri = recurly.base_uri() + endpoint.base_uri

            def list_callback(request, uri, headers, endpoint=endpoint):
                xml, item_count = endpoint.list()
                headers['X-Records'] = item_count
                return 200, headers, xml
            HTTPretty.register_uri(HTTPretty.GET, list_uri, body=callback(self)(list_callback), content_type="application/xml")

            def create_callback(request, uri, headers, endpoint=endpoint):
                return 200, headers, endpoint.create(deserialize(request.body)[1])
            HTTPretty.register_uri(HTTPretty.POST, list_uri, body=callback(self)(create_callback), content_type="application/xml")

            # register details views
            detail_uri = recurly.base_uri() + endpoint.base_uri + r'/([^/ ]+)'
            detail_uri_re = re.compile(detail_uri + r'$')

            def retrieve_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                pk = detail_uri_re.match(uri).group(1)
                return 200, headers, endpoint.retrieve(pk)
            HTTPretty.register_uri(HTTPretty.GET, detail_uri_re, body=callback(self)(retrieve_callback), content_type="application/xml")

            def update_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                pk = detail_uri_re.match(uri).group(1)
                return 200, headers, endpoint.update(pk, deserialize(request.body)[1])
            HTTPretty.register_uri(HTTPretty.PUT, detail_uri_re, body=callback(self)(update_callback), content_type="application/xml")

            def delete_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                parsed_url = urlparse(uri)
                pk = detail_uri_re.match('{0}://{1}{2}'.format(parsed_url.scheme, parsed_url.netloc, parsed_url.path)).group(1)
                endpoint.delete(pk, **parse_qs(parsed_url.query))
                return 204, headers, ''
            HTTPretty.register_uri(HTTPretty.DELETE, detail_uri_re, body=callback(self)(delete_callback))

            # register extra views
            for method in filter(lambda method: callable(method) and getattr(method, 'is_route', False), (getattr(endpoint, m) for m in dir(endpoint))):
                uri = detail_uri + '/' + method.uri
                uri_re = re.compile(uri)
                def extra_route_callback(request, uri, headers, method=method, uri_re=uri_re):
                    pk = uri_re.match(uri).group(1)
                    if method.method == 'DELETE':
                        status = 204
                    else:
                        status = 200
                    if request.method in ['POST', 'PUT']:
                        post_data = request.querystring.copy()
                        if request.body:
                            post_data.update(deserialize(request.body)[1])
                        result = method(pk, post_data)
                    elif method.is_list:
                        result = method(pk, filters=request.querystring)
                        headers['X-Records'] = result[1]
                        result = result[0]
                    else:
                        result = method(pk)
                    return status, headers, result
                if method.method == 'DELETE':
                    HTTPretty.register_uri(HTTPretty.DELETE, uri_re, body=callback(self)(extra_route_callback))
                else:
                    HTTPretty.register_uri(method.method, uri_re, body=callback(self)(extra_route_callback), content_type="application/xml")
