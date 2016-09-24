import collections.abc
import inspect
import re
import typing
import wsgiref.simple_server

import webob
import webob.exc

from . import mappers


def generate_sitemap(sitemap: typing.Mapping, prefix: list=None):
    """Create a sitemap template from the given sitemap.

    The `sitemap` should be a mapping where the key is a string which
    represents a single URI segment, and the value is either another mapping
    or a callable (e.g. function) object.

    Args:
        sitemap: The definition of the routes and their views
        prefix: The base url segment which gets prepended to the given map.

    Examples:
        The sitemap should follow the following format:
        >>> {
        >>>     'string_literal': {
        >>>         '': func1,
        >>>         '{arg}': func2,
        >>>     },
        >>> }

        The key points here are thus:
            - Any string key not matched by the following rule will be matched
              literally
            - Any string key surrounded by curly brackets matches a url segment
              which represents a parameter whose name is the enclosed string
              (i.e. should be a valid keyword argument)
            - *note* a side effect of this is that an empty string key will
              match all routes leading up to the current given mapping

        The above sitemap would compile to the following url mappings:
            - /string_literal/ -> calls `func1()`
            - /string_literal/{arg}/ -> calls `func2(arg=<the matched value>)`
    """
    if prefix is None:
        prefix = []

    for segment, sub_segment in sitemap.items():
        if isinstance(sub_segment, collections.abc.Mapping):
            yield from generate_sitemap(sub_segment, prefix + [segment])
        elif isinstance(sub_segment, collections.abc.Callable):
            if segment:
                prefix = prefix + [segment]
            yield (prefix, sub_segment)
        else:
            raise ValueError('Invalid datatype for sitemap')


def compile_route_regex(template):
    template = '/'.join(template)
    segment_regex = r'\{(\w+)\}'
    regex = ['^']
    last_position = 0
    for match in re.finditer(segment_regex, template):
        escaped_section = re.escape(template[last_position:match.start()])
        kwarg_name = match.group(1)

        regex.append(escaped_section)
        regex.append('(?P<{}>\w+)'.format(kwarg_name))
        last_position = match.end()
    regex.append(re.escape(template[last_position:]))
    regex.append('$')
    result = ''.join(regex)
    return result


def get_parameter_mappings(callable):
    result = {}
    sig = inspect.signature(callable)
    for name, param in sig.parameters.items():
        result[name] = param.annotation
    return result


def map_params(mappings, context):
    result = {}
    for name, value in context.items():
        mapping = mappings[name]
        if mapping == inspect.Signature.empty:
            result[name] = value
            continue
        result[name] = mapping(value)
    return result


def get_route_response(sitemap, route_template, request):
    route_template = iter(route_template)
    next(route_template)

    url_context = {}
    sitemap_context = sitemap
    for segment in route_template:
        keyword = None
        if segment.startswith('{') and segment.endswith('}'):
            keyword = segment[1:-1]
            url_context[keyword] = request.urlvars[keyword]

        resource_callable = None
        sitemap_context = sitemap_context[segment]

        if isinstance(sitemap_context, collections.abc.Callable):
            if segment:
                resource_callable = sitemap_context
        elif '' in sitemap_context:
            resource_callable = sitemap_context['']

        if resource_callable:
            param_mappings = get_parameter_mappings(resource_callable)
            url_context = map_params(param_mappings, url_context)
            response = resource_callable(request, **url_context)

            if keyword:
                url_context[keyword] = response
    return response


def get_callable_return_type(callable):
    signature = inspect.signature(callable)
    return_type = signature.return_annotation
    if return_type == inspect.Signature.empty:
        return None
    return signature.return_annotation


def inject_wsgi_types(request_type, response_type, base_exc_type):
    def make_route_response(sitemap, route_template, callable, conversion_type=mappers.Response):
        def replacement(env, start_response):
            request = request_type(env)
            try:
                response = get_route_response(sitemap, route_template, request)
            except base_exc_type as e:
                response = e
            else:
                response = conversion.get(response)
            return response(env, start_response)

        return_type = get_callable_return_type(callable)
        if return_type:
            conversion_type = return_type
        conversion = conversion_type(response_type)

        return replacement
    return make_route_response


class Tawdry():
    request_type = webob.Request
    response_type = webob.Response
    base_exc_type = webob.exc.HTTPException

    def __init__(self, sitemap=None, prefix=''):
        """

        Args:
            sitemap: asdf
            prefix: The base url segment which gets prepended to the given map.
                *note* the default of ''. This will cause the generated URI to be
                prefixed with '/'. If `None` is passed, there will be no prefix,
                but if any other string is passed, it should generally begin with
                a '/'.
        """
        if sitemap is None:
            sitemap = {}

        make_route_response = inject_wsgi_types(
            self.request_type,
            self.response_type,
            self.base_exc_type,
        )
        generated_sitemap = generate_sitemap(sitemap, [prefix])

        self._routes = []
        for route_template, callable in generated_sitemap:
            compiled_route = compile_route_regex(route_template)
            controller = make_route_response(sitemap, route_template, callable)
            self._routes.append((compiled_route, controller))

    def __call__(self, env, start_response):
        request = self.request_type(env)
        for regex, controller in self._routes:
            match = re.match(regex, request.path_info)
            if match:
                request.urlvars = match.groupdict()
                return controller(env, start_response)
        return webob.exc.HTTPNotFound()(env, start_response)

    def serve(self, make_server=wsgiref.simple_server.make_server, host='127.0.0.1', port=5000):
        httpd = make_server(host, port, self)
        print('Serving on http://{host}:{port}'.format(host=host, port=port))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('^C')
