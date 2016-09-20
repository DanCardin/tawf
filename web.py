import collections.abc
import inspect
import re
import typing

import webob
import webob.exc

import wsgiref.simple_server


def generate_sitemap(sitemap: typing.Mapping, prefix: str=''):
    """Create a sitemap template from the given sitemap.

    The `sitemap` should be a mapping where the key is a string which
    represents a single URI segment, and the value is either another mapping
    or a callable (e.g. function) object.

    Args:
        sitemap: The definition of the routes and their views
        prefix: The base url segment which gets prepended to the given map.
            *note* the default of ''. This will cause the generated URI to be
            prefixed with '/'. If `None` is passed, there will be no prefix,
            but if any other string is passed, should generally begin with
            a '/'.

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
    # Ensures all generated urls are prefixed with a the prefix string
    if prefix is None:
        prefix = []
    else:
        prefix = [prefix]

    for segment, sub_segment in sitemap.items():
        segment = [segment]
        if isinstance(sub_segment, collections.abc.Mapping):
            yield from generate_sitemap(sub_segment, prefix + segment)
        elif isinstance(sub_segment, collections.abc.Callable):
            result = prefix
            if segment:
                result = result + segment
            yield (result, sub_segment)
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


def make_controller(sitemap, route_template, callable):
    def get_url_vars(sitemap, route_template, request):
        route_template = iter(route_template)
        next(route_template)

        url_context = {}
        sitemap_context = sitemap
        for segment in route_template:
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

                url_context[keyword] = response
        return response

    def replacement(env, start_response):
        request = webob.Request(env)
        try:
            response = get_url_vars(sitemap, route_template, request)
            response = str(response)
        except webob.exc.HTTPException as e:
            response = e

        if not isinstance(response, webob.exc.HTTPException):
            response = webob.Response(body=response)

        return response(env, start_response)
    return replacement


class Router():
    def __init__(self, routes):
        self._routes = routes

    def __call__(self, env, start_response):
        request = webob.Request(env)
        for regex, controller in self._routes:
            match = re.match(regex, request.path_info)
            if match:
                request.urlvars = match.groupdict()
                return controller(env, start_response)
        return webob.exc.HTTPNotFound()(env, start_response)


def serve(sitemap, make_server=wsgiref.simple_server.make_server, host='127.0.0.1', port=5000):
    generated_sitemap = generate_sitemap(sitemap)

    routes = []
    for route_template, callable in generated_sitemap:
        compiled_route = compile_route_regex(route_template)
        controller = make_controller(sitemap, route_template, callable)
        routes.append((compiled_route, controller))

    app = Router(routes)

    httpd = make_server(host, port, app)
    print('Serving on http://{host}:{port}'.format(host=host, port=port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('^C')


if __name__ == '__main__':
    def publisher(request, publisher_id: int) -> 'JsonResponse[list]':
        return {'name': 'Mad Hat'}

    def author(request, publisher_id, author_id):
        return {'name': 'Sonny Jim', 'pubname': publisher_id['name']}

    def book(request, publisher_id, author_id, book_id):
        return {'name': author_id['name'] + ' - The Book'}

    author_sitemap = {
        'author': {
            '{author_id}': {
                '': author,
                'book': {
                    '{book_id}': book,
                },
            },
        },
    }

    sitemap = {
        'publisher': {
            '{publisher_id}': {
                '': publisher,
                **author_sitemap,
            },
        },
    }

    serve(sitemap, port=6001)
