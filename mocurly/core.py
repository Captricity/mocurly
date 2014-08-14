import os
import re
import xml.dom.minidom as minidom
from httpretty import HTTPretty
from jinja2 import Template

PROJECT_DIR = os.path.dirname(__file__)

def details_route(method, uri):
    def details_route_decorator(func):
        func.is_route = True
        func.method = method
        func.uri = uri
        return func
    return details_route_decorator

def serialize(template, object_type, object_dict):
    # Takes in the object type + dictionary representation and returns the XML
    template = Template(open(os.path.join(PROJECT_DIR, template)).read())
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
    raise NotImplementedError

def _deserialize_item(root):
    object_type = root.tagName
    obj = {}
    for node in root.childNodes:
        if node.hasAttribute('nil'):
            obj[node.tagName] = None
        elif len(node.childNodes) == 1 and node.childNodes[0].nodeType == minidom.Node.TEXT_NODE:
            obj[node.tagName] = node.firstChild.nodeValue
        else:
            child_object_type, child_object = _deserialize_item(node)
            obj[node.tagName] = child_object
    return object_type, obj

class BaseRecurlyEndpoint(object):
    def list(self):
        raise NotImplementedError

    def uris(self, obj):
        cls = self.__class__
        uri_out = {}
        uri_out['object_uri'] = BASE_URI + cls.base_uri + '/' + obj[cls.pk_attr]
        return uri_out

    def serialize(self, obj):
        cls = self.__class__
        obj['uris'] = self.uris(obj)
        return serialize(cls.template, cls.object_type, obj)

    def create(self, create_info):
        cls = self.__class__
        create_info['uuid'] = create_info[cls.pk_attr]
        new_obj = cls.backend.add_object(create_info)
        return self.serialize(new_obj)

    def retrieve(self, pk):
        cls = self.__class__
        return self.serialize(cls.backend.get_object(pk))

    def update(self, pk, update_info):
        cls = self.__class__
        return self.serialize(cls.backend.update_object(pk, update_info))

    def delete(self, pk):
        cls = self.__class__
        cls.backend.delete_object(pk)
 
BASE_URI = 'https://api.recurly.com/v2' # TODO
def register():
    from .endpoints import AccountsEndpoint

    endpoints = [AccountsEndpoint()] # TODO
    for endpoint in endpoints:
        # register list views
        list_uri = BASE_URI + endpoint.base_uri

        def list_callback(request, uri, headers):
            return 200, headers, endpoint.list()
        HTTPretty.register_uri(HTTPretty.GET, list_uri, body=list_callback, content_type="application/xml")

        def create_callback(request, uri, headers):
            return 200, headers, endpoint.create(deserialize(request.parsed_body)[1])
        HTTPretty.register_uri(HTTPretty.POST, list_uri, body=create_callback, content_type="application/xml")

        # register details views
        detail_uri = BASE_URI + endpoint.base_uri + r'/([^/ ]+)'
        detail_uri_re = re.compile(detail_uri)

        def retrieve_callback(request, uri, headers):
            pk = detail_uri_re.match(uri).group(1)
            return 200, headers, endpoint.retrieve(pk)
        HTTPretty.register_uri(HTTPretty.GET, detail_uri_re, body=retrieve_callback, content_type="application/xml")

        def update_callback(request, uri, headers):
            pk = detail_uri_re.match(uri).group(1)
            return 200, headers, endpoint.update(pk, deserialize(request.parsed_body)[1])
        HTTPretty.register_uri(HTTPretty.PUT, detail_uri_re, body=update_callback, content_type="application/xml")

        def delete_callback(request, uri, headers):
            pk = detail_uri_re.match(uri).group(1)
            return 204, headers, ''
        HTTPretty.register_uri(HTTPretty.DELETE, detail_uri_re, body=delete_callback)

        # register extra views
        for method in filter(lambda method: callable(method) and getattr(method, 'is_route', False), (getattr(endpoint, m) for m in dir(endpoint))):
            uri = detail_uri + '/' + method.uri
            uri_re = re.compile(uri)
            def callback(request, uri, headers, method=method):
                pk = uri_re.match(uri).group(1)
                if method.method == 'DELETE':
                    status = 204
                else:
                    status = 200
                if request.method in ['POST', 'PUT']:
                    result = method(pk, deserialize(request.parsed_body)[1])
                else:
                    result = method(pk)
                return status, headers, result
            if method.method == 'DELETE':
                HTTPretty.register_uri(method.method, uri_re, body=callback)
            else:
                HTTPretty.register_uri(method.method, uri_re, body=callback, content_type="application/xml")
