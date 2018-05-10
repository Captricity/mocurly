"""Core functions used to interface into mocurly

Exposes the main mocurly class which is the gateway into setting up the mocurly
context.
"""
import recurly
import re
import ssl
import functools
from six.moves.urllib.parse import urlparse, parse_qs, unquote
from httpretty import HTTPretty

from .utils import deserialize
from .errors import ResponseError
from .backend import clear_backends


class mocurly(object):
    """Main class that provides the mocked context.

    This can be used as a decorator, as a context manager, or manually. In all
    three cases, the guarded context will route all recurly requests to the
    mocked callback functions defined in endpoints.py.
    """
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

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)

    def start(self):
        """Starts the mocked context by enabling HTTPretty to route requests to
        the defined endpoints.
        """
        from .endpoints import clear_endpoints
        self.started = True
        clear_endpoints()
        clear_backends()

        if not HTTPretty.is_enabled():
            HTTPretty.enable()

        self._register()

    def stop(self):
        """Stops the mocked context, restoring the routes back to what they were
        """
        if not self.started:
            raise RuntimeError('Called stop() before start()')

        HTTPretty.disable()

    def start_timeout(self, timeout_filter=None):
        """Notifies mocurly to start simulating time outs within the current
        context.

        You can pass in a filter function which will be used to decide what
        requests to timeout. The function will get one parameter, `request`,
        which is an instance of the HTTPrettyRequest class, and should return a
        boolean which when True, the request will time out.

        The following attributes are available on the request object:
            `headers` -> a mimetype object that can be cast into a dictionary,
            contains all the request headers.

            `method` -> the HTTP method used in this request.

            `path` -> the full path to the requested URI.

            `querystring` -> a dictionary containing lists with the attributes.

            `body` -> the raw contents of the request body.

            `parsed_body` -> a dictionary containing parsed request body or
                `None` if `HTTPrettyRequest` doesn't know how to parse it.
        """
        self.timeout_filter = timeout_filter
        self.timeout_connection = True

    def should_timeout(self, request):
        if self.timeout_filter is None or self.timeout_filter(request):
            return self.timeout_connection
        return False

    def stop_timeout(self):
        """Notifies mocurly to stop simulating time outs within the current
        context.
        """
        self.timeout_filter = None
        self.timeout_connection = False

    def start_timeout_successful_post(self, timeout_filter=None):
        """Notifies mocurly to make timeouts on POST requests, but only after
        it has caused state changes.

        Like `start_timeout`, you can pass in a filter function used to decide
        which requests to cause the timeout on.
        """
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
        """Notifies mocurly to stop simulating successful POST time outs within
        the current context.
        """
        self.timeout_filter = None
        self.timeout_connection_successful_post = False

    def register_transaction_failure(self, account_code, error_code):
        """Register a transaction failure for the given account.

        This will setup mocurly such that all transactions made by the account
        with the given `account_code` will fail with the selected `error_code`.
        """
        from .endpoints import transactions_endpoint
        transactions_endpoint.register_transaction_failure(account_code, error_code)

    def _register(self):
        """Walks the endpoints to register all its URIs to HTTPretty so that
        they can mock recurly requests.
        """
        from .endpoints import endpoints
        for endpoint in endpoints:
            # register list views
            list_uri = recurly.base_uri() + endpoint.base_uri
            list_uri_re = re.compile(list_uri + r'$')

            def list_callback(request, uri, headers, endpoint=endpoint):
                xml, item_count = endpoint.list()
                headers['X-Records'] = item_count
                return 200, headers, xml
            HTTPretty.register_uri(
                HTTPretty.GET,
                list_uri_re,
                body=_callback(self)(list_callback),
                content_type="application/xml")

            def create_callback(request, uri, headers, endpoint=endpoint):
                return 200, headers, endpoint.create(deserialize(request.body)[1])
            HTTPretty.register_uri(
                HTTPretty.POST,
                list_uri_re,
                body=_callback(self)(create_callback),
                content_type="application/xml")

            # register details views
            detail_uri = recurly.base_uri() + endpoint.base_uri + r'/([^/ ]+)'
            detail_uri_re = re.compile(detail_uri + r'$')

            def retrieve_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                raw_pk = detail_uri_re.match(uri).group(1)
                pk = unquote(raw_pk)
                return 200, headers, endpoint.retrieve(pk)
            HTTPretty.register_uri(
                HTTPretty.GET,
                detail_uri_re,
                body=_callback(self)(retrieve_callback),
                content_type="application/xml")

            def update_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                raw_pk = detail_uri_re.match(uri).group(1)
                pk = unquote(raw_pk)
                return 200, headers, endpoint.update(pk, deserialize(request.body)[1])
            HTTPretty.register_uri(
                HTTPretty.PUT,
                detail_uri_re,
                body=_callback(self)(update_callback),
                content_type="application/xml")

            def delete_callback(request, uri, headers, endpoint=endpoint, detail_uri_re=detail_uri_re):
                parsed_url = urlparse(uri)
                url_domain_part = '{0}://{1}{2}'.format(parsed_url.scheme, parsed_url.netloc, parsed_url.path)
                raw_pk = detail_uri_re.match(url_domain_part).group(1)
                pk = unquote(raw_pk)
                endpoint.delete(pk, **parse_qs(parsed_url.query))
                return 204, headers, ''
            HTTPretty.register_uri(
                HTTPretty.DELETE,
                detail_uri_re,
                body=_callback(self)(delete_callback))

            # register extra views
            extra_views = filter(
                lambda method: callable(method) and getattr(method, 'is_route', False),
                (getattr(endpoint, m)
                 for m in dir(endpoint)))
            for method in extra_views:
                uri = detail_uri + '/' + method.uri
                uri_re = re.compile(uri)

                def extra_route_callback(
                        request,
                        uri,
                        headers,
                        method=method,
                        uri_re=uri_re):
                    uri_args = uri_re.match(uri).groups()
                    uri_args = list(uri_args)
                    uri_args[0] = unquote(uri_args[0])
                    if method.method == 'DELETE':
                        status = 204
                    else:
                        status = 200
                    if request.method in ['POST', 'PUT']:
                        post_data = request.querystring.copy()
                        if request.body:
                            post_data.update(deserialize(request.body)[1])
                        uri_args.append(post_data)
                        result = method(*uri_args)
                    elif method.is_list:
                        result = method(*uri_args, filters=request.querystring)
                        headers['X-Records'] = result[1]
                        result = result[0]
                    else:
                        result = method(*uri_args)
                    return status, headers, result
                if method.method == 'DELETE':
                    HTTPretty.register_uri(HTTPretty.DELETE, uri_re, body=_callback(self)(extra_route_callback))
                else:
                    HTTPretty.register_uri(method.method, uri_re, body=_callback(self)(extra_route_callback), content_type="application/xml")


class _callback(object):
    """Decorator for setting up callback functions to be used in the mocurly
    context.

    This will handle the machinery behind timeout and error simulation.
    """
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
                # Pass through response errors in a way that httpretty will
                # respond with the right status code and message
                if not self.mocurly_instance.should_timeout_successful_post(request):
                    return exc.status_code, headers, exc.response_body

            if self.mocurly_instance.should_timeout_successful_post(request):
                raise ssl.SSLError('The read operation timed out')

            return return_val
        return wrapped
