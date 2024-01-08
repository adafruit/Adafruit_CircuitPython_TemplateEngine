Simple test
------------

This is the minimal example of using the library.
This example is printing a basic HTML page with with a dynamic paragraph.

.. literalinclude:: ../examples/templateengine_simpletest.py
    :caption: examples/templateengine_simpletest.py
    :lines: 5-
    :linenos:

Reusing templates
-----------------

The are two main ways of rendering templates:

- using one of ``render_...`` methods
- manually creating a ``Template`` object and calling its method

While the first method is simpler, it also compiles the template on every call.
The second method is more efficient when rendering the same template multiple times, as it allows
to reuse the compiled template, at the cost of more memory usage.

Both methods can be used interchangeably, as they both return the same result.
It is up to the user to decide which method is more suitable for a given use case.

**Generally, the first method will be sufficient for most use cases.**

It is also worth noting that compiling all used templates using the second method might not be possible,
depending on the project and board used, due to the limited amount of RAM.

.. literalinclude:: ../examples/templateengine_reusing.py
    :caption: examples/templateengine_reusing.py
    :lines: 5-
    :emphasize-lines: 1,16,20
    :linenos:

Expressions
-----------

Token ``{{ ... }}`` is used for evaluating expressions.

The most basic use of the template engine is to replace some parts of a template with values.
Those values can be passed as a ``dict``, which is often called ``context``, to the template.


This functionality works very similarly to Python's f-strings.

Every expression that would be valid in an f-string is also valid in the template engine.

This includes, but is not limited to:

- mathemathical operations e.g. ``{{ 5 + 2 ** 3 }}`` will be replaced with ``"13"``
- string operations e.g. ``{{ 'hello'.upper() }}`` will be replaced with ``"HELLO"``
- logical operations e.g. ``{{ 1 == 2 }}`` will be replaced with ``"False"``
- ternary operator e.g. ``{{ 'ON' if True else 'OFF' }}`` will be replaced with ``"ON"``
- built-in functions e.g. ``{{ len('Adafruit Industries') }}`` will be replaced with ``"19"``

Of course, values from the ``context`` can also be used in all of the above expressions.

**Values are not directly available in templates, instead you should access them using the** ``context``.

.. literalinclude:: ../examples/templateengine_expressions.py
    :caption: examples/templateengine_expressions.py
    :lines: 5-
    :emphasize-lines: 11,13,15-16,18
    :linenos:


``if`` statements
-----------------

Token ``{% if ... %} ... {% endif %}`` is used for simple conditional rendering.
It can be used with optional ``{% elif ... %}`` and ``{% else %}`` tokens, with corresponding blocks.

Any Python logical expression can be used inside the ``{% if ... %}`` and ``{% elif ... %}`` token.

This includes, but is not limited to:

- ``==`` - equal
- ``!=`` - not equal
- ``<`` - less than
- ``>`` - greater than
- ``<=`` - less than or equal
- ``>=`` - greater than or equal
- ``in`` - check if a value is in a sequence
- ``not`` - negate a logical expression
- ``and`` - logical and
- ``or`` - logical or
- ``is`` - check if two objects are the same

.. literalinclude:: ../examples/templateengine_if_statements.py
    :caption: examples/templateengine_if_statements.py
    :lines: 5-
    :emphasize-lines: 11-17
    :linenos:

``for`` loops
-------------

Token ``{% for ... in ... %} ... {% endfor %}`` is used for iterating over a sequence.

Additionally, ``{% empty %}`` can be used to specify a block that will be rendered if the sequence is empty.

.. literalinclude:: ../examples/templateengine_for_loops.py
    :caption: examples/templateengine_for_loops.py
    :lines: 5-
    :emphasize-lines: 14-18
    :linenos:

``while`` loops
---------------

Token ``{% while ... %} ... {% endwhile %}`` is used for rendering a block multiple times,
until the condition is met.

By itself, this token is not very useful, most of the time, using ``{% for ... in ... %}`` is a better choice.
The ``{% exec ... %}`` token, which is described later, can be used to modify the varaible which is used in the
condition, thus allowing for breaking out of the loop.

Saying that, even without using ``{% exec ... %}``, ``{% while ... %}`` can be used by itself:

.. literalinclude:: ../examples/templateengine_while_loops.py
    :caption: examples/templateengine_while_loops.py
    :lines: 5-
    :emphasize-lines: 15-17
    :linenos:


Including templates from other files
------------------------------------

When writing a template, it is often useful to split it into multiple files.

Token ``{% include ... %}`` is used for including templates from other files.
There is no support for dynamic includes, only static or hardcoded paths are supported.

This is often used to e.g. move a navigation bar of a website or footer into a separate file,
and then include it in multiple pages.

.. literalinclude:: ../examples/footer.html
    :caption: examples/footer.html
    :lines: 7-
    :language: html
    :linenos:

.. literalinclude:: ../examples/base_without_footer.html
    :caption: examples/base_without_footer.html
    :lines: 7-
    :language: html
    :emphasize-lines: 12
    :linenos:

.. literalinclude:: ../examples/templateengine_includes.py
    :caption: examples/templateengine_includes.py
    :lines: 5-
    :linenos:

Blocks and extending templates
------------------------------

Sometimes seaprating different parts of a template into different files is not enough.
That is where template inheritance comes in.

Token ``{% block ... %} ... {% endblock ... %}`` is used for defining blocks in templates, note that block must always
have a name and end with a corresponding named endblock tag.

The only exception from this are block defined in a top level template (the one taht does not extend any other template).
They are allowed to nothave a endblock tag.

A very common use case is to have a base template, which is then extended by other templates.
This allows sharing whole layout, not only single parts.

.. literalinclude:: ../examples/child.html
    :caption: examples/child.html
    :lines: 7-
    :language: html
    :linenos:

.. literalinclude:: ../examples/parent_layout.html
    :caption: examples/parent_layout.html
    :lines: 7-
    :language: html
    :linenos:

.. literalinclude:: ../examples/templateengine_blocks_extends.py
    :caption: examples/templateengine_blocks_extends.py
    :lines: 5-
    :linenos:

In the above example, ``{% block footer %}`` will be removed, as the child template does not provide any content for it.
On the other hand ``{% block title %}`` will contain both the content from the parent template and the child template,
because the child template uses ``{{ block.super }}`` to render the content from the parent template.

Executing Python code in templates
----------------------------------

It is also possible to execute Python code in templates.
This can be used for e.g. defining variables, modifying context, or breaking from loops.


.. literalinclude:: ../examples/templateengine_exec.py
    :caption: examples/templateengine_exec.py
    :lines: 5-
    :emphasize-lines: 12,15,18,21,28,33
    :linenos:

Notice that varaibles defined in ``{% exec ... %}`` are do not have to ba accessed using ``context``,
but rather can be accessed directly.

Comments in templates
---------------------

Template engine supports comments that are removed completely from the rendered output.

Supported comment syntaxes:

- ``{# ... #}`` - for single-line comments
- ``{% comment %} ... {% endcomment %}`` - for multi-line comments
- ``{% comment "..." %} ... {% endcomment %}`` - for multi-line comments with optional note (both ``"`` and ``'`` are supported)

.. literalinclude:: ../examples/comments.html
    :caption: examples/comments.html
    :lines: 7-
    :language: html
    :linenos:

.. literalinclude:: ../examples/templateengine_comments.py
    :caption: examples/templateengine_comments.py
    :lines: 5-
    :linenos:

Autoescaping unsafe characters
------------------------------

Token ``{% autoescape off %} ... {% endautoescape %}`` is used for marking a block of code that should
be not be autoescaped. Consequently using ``{% autoescape off %} ...`` does the opposite and turns
the autoescaping back on.

By default the template engine will escape all HTML-unsafe characters in expressions
(e.g. ``<`` will be replaced with ``&lt;``).

Content outside expressions is not escaped and is rendered as-is.

For escaping XML and Markdown, you can use the ``language=`` parameter, both in ``render_...`` methods
and in all ``Template`` constructors.

.. literalinclude:: ../examples/autoescape.html
    :caption: examples/autoescape.html
    :lines: 7-
    :language: html
    :linenos:

.. literalinclude:: ../examples/autoescape.md
    :caption: examples/autoescape.md
    :lines: 5-
    :language: markdown
    :linenos:

.. literalinclude:: ../examples/templateengine_autoescape.py
    :caption: examples/templateengine_autoescape.py
    :lines: 5-
    :linenos:
