"""Utility functions that help the development
"""
import pytz
import datetime
from xml.dom import minidom

from jinja2 import Environment, PackageLoader
jinja2_env = Environment(loader=PackageLoader('mocurly', 'templates'), extensions=['jinja2.ext.with_'])


def current_time():
    """Returns the current time in UTC, with the timezone set
    """
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def details_route(method, uri, is_list=False):
    """A decorator for Endpoint classes to define a custom URI.

    Extends the endpoint's details route. For example, suppose the following
    method was defined on an endpoint with the base uri as `foo`:

    ::

        @details_route('GET', 'bar')
        def bar_callback(self, pk):
            return response

    This will generate a new endpoint /foo/:pk/bar that routes to the
    `bar_callback` method.
    """
    def details_route_decorator(func):
        func.is_route = True
        func.method = method
        func.uri = uri
        func.is_list = is_list
        return func
    return details_route_decorator


def serialize_list(template, object_type_plural, object_type, object_list):
    """Serializes a list of resource objects into its XML version.

    Accepts:
        template - The jinja2 template to use to generate the XML
        object_type_plural - Plural notation for the object type
        object_type - String representation of the object type
        object_list - The list of object to be serialized

    Returns:
        An XML string representing the serialized object list
    """
    serialized_obj_list = []
    for obj in object_list:
        serialized_obj_list.append(serialize(template, object_type, obj))
    return '<{0} type="array">{1}</{0}>'.format(object_type_plural, ''.join(serialized_obj_list)), len(serialized_obj_list)


def serialize(template, object_type, object_dict):
    """Serializes a resource object into its XML version.

    Accepts:
        template - The jinja2 template to use to generate the XML
        object_type - String representation of the object type
        object_dict - The object to be serialized

    Returns:
        An XML string representing the serialized object list
    """
    template = jinja2_env.get_template(template)
    kwargs = {}
    kwargs[object_type] = object_dict
    return template.render(**kwargs)


def deserialize(xml):
    """Deserialize the XML string into an object

    Accepts:
        xml - XML string representing a resource object

    Returns:
        Tuple of object_type and the object as a dictionary. The type can be
        used to resolve what endpoint or object store to route to.
    """
    parsed_xml = minidom.parseString(xml)
    # only know of xml input with 1 child node, since thats all there is to
    # recurly
    assert len(parsed_xml.childNodes) == 1
    root = parsed_xml.firstChild
    if root.hasAttribute('type') and root.getAttribute('type') == 'array':
        return _deserialize_list(root)
    else:
        return _deserialize_item(root)


def _deserialize_list(root):
    """Deserializes a list of objects into their dictionary form.
    """
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
