import webob

from tawdry import mappers, Tawdry


def publishers(request) -> mappers.JsonResponse[list]:
    return [{'name': 'Mad Hat'}, {'name': 'Harambe'}]


def publisher(request, publisher_id: int):
    return 'Mad Hat'


def author(request, publisher_id, author_id) -> mappers.XmlResponse[dict]:
    return {'name': 'Sonny Jim', 'publisher': {'name': 'Harambe'}}


def book(request, publisher_id, author_id, book_id) -> mappers.JsonResponse[dict]:
    return {
        'name': author_id['name'] + ' - The Book',
        'version': 1.,
        'sequels': None,
    }


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
        '': publishers,
        '{publisher_id}': {
            '': publisher,
            **author_sitemap,
        },
    },
}


def test_get_publisher():
    tawdry = Tawdry(sitemap)
    request = webob.Request.blank('/publisher/4')
    response = request.get_response(tawdry)
    assert response.body == b'Mad Hat'


def test_get_author():
    tawdry = Tawdry(sitemap)
    request = webob.Request.blank('/publisher/4/author/1')
    response = request.get_response(tawdry)
    assert response.body == (
        b'<objects name="Sonny Jim">'
        b'<publisher name="Harambe"/>'
        b'</objects>'
    )


def test_get_book():
    tawdry = Tawdry(sitemap)
    request = webob.Request.blank('/publisher/4/author/1/book/7')
    response = request.get_response(tawdry)
    assert response.body == (
        b'{'
        b'"name": "Sonny Jim - The Book", '
        b'"sequels": null, '
        b'"version": 1.0'
        b'}'
    )
