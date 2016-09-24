import collections.abc
import functools
import json


class TypingMeta(type):
    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, name, bases, namespace, *parameters):
        self = super().__new__(cls, name, bases, namespace)
        if parameters:
            self.__param__, *_ = parameters
            return self

        return self

    def __instancecheck__(self, obj):
        if self.__param__ and isinstance(obj, self.__param__):
            return True
        return False

    @functools.lru_cache(typed=True)
    def __getitem__(self, *params):
        assert len(params) == 1
        return self.__class__(
            self.__name__,
            self.__bases__,
            dict(self.__dict__),
            *params,
        )

    def __repr__(self):
        return '{}[{}]'.format(super().__repr__(), self.__param__)


class Response(metaclass=TypingMeta):
    def __init__(self, response_type):
        self._response_type = response_type

    def _create_response(self, result):
        return self._response_type(body=result)

    def _set_content_type(self, response):
        response.headers.add('Content-type', 'text/html')

    def get(self, result):
        response = self._create_response(result)
        self._set_content_type(response)
        return response


class JsonResponse(Response):
    __param__ = type(None)

    def _set_content_type(self, response):
        response.headers.add('Content-type', 'application/json')

    def get(self, result):
        assert isinstance(result, self.__param__)
        result = json.dumps(result, sort_keys=True)
        return Response.get(self, result)


class XmlResponse(Response):
    __param__ = type(None)

    def _set_content_type(self, response):
        response.headers.add('Content-type', 'application/xml')

    @staticmethod
    def convert_to_xml(map, root_node='objects'):
        xml_result = []
        if isinstance(map, collections.abc.Mapping):
            children = []
            attributes = []
            for key, value in map.items():
                if isinstance(value, str):
                    attributes.append(' {}="{}"'.format(key, str(value)))
                else:
                    children.append(XmlResponse.convert_to_xml(value, key))

            xml_result.append(
                '<{node}{attributes}{maybe_trailing_slash}>'.format(
                    node=root_node,
                    attributes=' '.join(attributes),
                    maybe_trailing_slash='' if children else '/',
                )
            )
            xml_result.extend(children)
            if children:
                xml_result.append('</{node}>'.format(node=root_node))
        else:
            for value in map:
                xml_result.append(XmlResponse.convert_to_xml(value, 'object'))

        return ''.join(xml_result)

    def get(self, result):
        assert isinstance(result, self.__param__)

        xml_response = XmlResponse.convert_to_xml(result)
        return Response.get(self, xml_response)
