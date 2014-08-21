import recurly
import re
import xml.dom.minidom as minidom
from six.moves.urllib.parse import urlparse, parse_qs
from httpretty import HTTPretty
from jinja2 import Environment, PackageLoader
jinja2_env = Environment(loader=PackageLoader('mocurly', 'templates'), extensions=['jinja2.ext.with_'])

from .backend import clear_backends

def details_route(method, uri, is_list=False):
    def details_route_decorator(func):
        func.is_route = True
        func.method = method
        func.uri = uri
        func.is_list = is_list
        return func
    return details_route_decorator

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
        self.started = True
        clear_backends()

        if not HTTPretty.is_enabled():
            HTTPretty.enable()

        self._register()

    def stop(self):
        if not self.started:
            raise RuntimeError('Called stop() before start()')

        HTTPretty.disable()

    def _register(self):
        from .endpoints import AccountsEndpoint
        from .endpoints import AdjustmentsEndpoint
        from .endpoints import TransactionsEndpoint
        from .endpoints import CouponsEndpoint
        from .endpoints import InvoicesEndpoint
        from .endpoints import PlansEndpoint
        from .endpoints import SubscriptionsEndpoint

        endpoints = [AccountsEndpoint(),
                AdjustmentsEndpoint(),
                TransactionsEndpoint(),
                CouponsEndpoint(),
                InvoicesEndpoint(),
                PlansEndpoint(),
                SubscriptionsEndpoint()]
        for endpoint in endpoints:
            # register list views
            list_uri = recurly.base_uri() + endpoint.base_uri

            def list_callback(request, uri, headers, endpoint=endpoint):
                xml, item_count = endpoint.list()
                headers['X-Records'] = item_count
                return 200, headers, xml
            HTTPretty.register_uri(HTTPretty.GET, list_uri, body=list_callback, content_type="application/xml")

            def create_callback(request, uri, headers, endpoint=endpoint):
                return 200, headers, endpoint.create(deserialize(request.body)[1])
            HTTPretty.register_uri(HTTPretty.POST, list_uri, body=create_callback, content_type="application/xml")

            # register details views
            detail_uri = recurly.base_uri() + endpoint.base_uri + r'/([^/ ]+)'
            detail_uri_re = re.compile(detail_uri + r'$')

            def retrieve_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                pk = detail_uri_re.match(uri).group(1)
                return 200, headers, endpoint.retrieve(pk)
            HTTPretty.register_uri(HTTPretty.GET, detail_uri_re, body=retrieve_callback, content_type="application/xml")

            def update_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                pk = detail_uri_re.match(uri).group(1)
                return 200, headers, endpoint.update(pk, deserialize(request.body)[1])
            HTTPretty.register_uri(HTTPretty.PUT, detail_uri_re, body=update_callback, content_type="application/xml")

            def delete_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                parsed_url = urlparse(uri)
                pk = detail_uri_re.match('{0}://{1}{2}'.format(parsed_url.scheme, parsed_url.netloc, parsed_url.path)).group(1)
                endpoint.delete(pk, **parse_qs(parsed_url.query))
                return 204, headers, ''
            HTTPretty.register_uri(HTTPretty.DELETE, detail_uri_re, body=delete_callback)

            # register extra views
            for method in filter(lambda method: callable(method) and getattr(method, 'is_route', False), (getattr(endpoint, m) for m in dir(endpoint))):
                uri = detail_uri + '/' + method.uri
                uri_re = re.compile(uri)
                def callback(request, uri, headers, method=method, uri_re=uri_re):
                    pk = uri_re.match(uri).group(1)
                    if method.method == 'DELETE':
                        status = 204
                    else:
                        status = 200
                    if request.method in ['POST', 'PUT']:
                        result = method(pk, deserialize(request.body)[1])
                    else:
                        result = method(pk)
                    if method.is_list:
                        headers['X-Records'] = result[1]
                        result = result[0]
                    return status, headers, result
                if method.method == 'DELETE':
                    HTTPretty.register_uri(method.method, uri_re, body=callback)
                else:
                    HTTPretty.register_uri(method.method, uri_re, body=callback, content_type="application/xml")
