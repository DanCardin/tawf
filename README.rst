Tawdry
======

*Tawdry* is a Type Annotated Web framework which emphasizes Dont Repeat Yourself

More specifically, *Tawdry* is a "*microframework*" similar to *flask* or
somewhat less similar to Pyramid or Django. It tries to get out of your way
by requiring the absolute minimal amount of boilerplate or extra code of any
kind.

*Tawdry* also aims to improve the clarity of the code you *do* write by
centralizing and localizing the information about your server and its routes.

Example Application
-------------------

.. code-block:: python

    import tawdry

    def hello(request, publisher):
        return 'World!'

    app = tawdry.Tawdry({'hello': hello})

    if __name__ == '__main__':
        app.serve()

Once run, it will create a single route at `/hello`, on localhost by default.

.. code-block:: bash

    $ curl localhost:5000/hello
    World!

Installation
------------

.. code-block:: python

    pip install tawdry

Requires Python 3 (and you're best off with 3.5)

Type Annotations
----------------

The above example doesn't really do much to show the purpose of *Tawdry* though.
The whole point here is to use type annotations, as they are the mechanism
through which *Tawdry* does its stuff! So lets look at a slightly more complex
example.

.. code-block:: python

    import tawdry

    def exclaim(request, exclamation: str) -> Response:
        return exclamation + '!'

    sitemap = {
        'exclaim': {
            '{exclamation}': exclaim,
        },
    }
    app = tawdry.Tawdry(sitemap)

    if __name__ == '__main__':
        app.serve()

.. code-block:: bash

    $ curl localhost:5000/exclaim/wahhoooo
    wahhoooo!

Of note in the above example:

* An argument type annotation will convert the argument to the annotated type
  before calling the function.

* A return type, type annotation will convert the function's return value
  after it returns.

* The `sitemap` is a dict given in the form where:

  + The values are the functions which will be called in the event of a match.

  + The keys match a url segment with the same string, so nested dictionaries
    result in matches to subsequent nested segments.

  + Any key enclosed in curly braces is given as a parameter to the function
    given as a value, as well as any parameters leading up to it.

So in the above example:

1. the sitemap defines a single manifested route in the form
   `/exclaim/{paramerer}`.
2. `parameter` will be converted (in this case unnecessarily) to a string before
   being passed to `exclaim`.
3. The return value of `exclaim` will be converted to a `Response` object
   (*note* `Response` is applied by default, but other return types exist, such
   as `JsonResponse` and `XmlResponse`)
4. The `Response` object is wsgi compatible and will return the result to
   the caller
