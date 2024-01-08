# SPDX-FileCopyrightText: Copyright (c) 2023 Michał Pokusa, Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
`adafruit_templateengine`
================================================================================

Templating engine to substitute variables into a template string.
Templates can also include conditional logic and loops. Often used for web pages.


* Author(s): Michał Pokusa, Tim Cocks

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_TemplateEngine.git"

try:
    from typing import Any, Generator
except ImportError:
    pass

import os
import re

try:
    from sys import implementation

    if implementation.name == "circuitpython" and implementation.version < (9, 0, 0):
        print(
            "Warning: adafruit_templateengine requires CircuitPython 9.0.0, as previous versions"
            " will have limited functionality when using block comments and non-ASCII characters."
        )
finally:
    # Unimport sys to prevent accidental use
    del implementation


class Language:  # pylint: disable=too-few-public-methods
    """
    Enum-like class that contains languages supported for escaping.
    """

    HTML = "html"
    """HTML language"""

    XML = "xml"
    """XML language"""

    MARKDOWN = "markdown"
    """Markdown language"""


def safe_html(value: Any) -> str:
    """
    Encodes unsafe symbols in ``value`` to HTML entities and returns the string that can be safely
    used in HTML.

    Examples::

        safe_html('<a href="https://circuitpython.org/">CircuitPython</a>')
        # &lt;a href&equals;&quot;https&colon;&sol;&sol;circuitpython&period;org&sol;&quot;&gt;...

        safe_html(10 ** (-10))
        # 1e&minus;10
    """

    def _replace_amp_or_semi(match: re.Match):
        return "&amp;" if match.group(0) == "&" else "&semi;"

    return (
        # Replace initial & and ; together
        re.sub(r"&|;", _replace_amp_or_semi, str(value))
        # Replace other characters
        .replace('"', "&quot;")
        .replace("_", "&lowbar;")
        .replace("-", "&minus;")
        .replace(",", "&comma;")
        .replace(":", "&colon;")
        .replace("!", "&excl;")
        .replace("?", "&quest;")
        .replace(".", "&period;")
        .replace("'", "&apos;")
        .replace("(", "&lpar;")
        .replace(")", "&rpar;")
        .replace("[", "&lsqb;")
        .replace("]", "&rsqb;")
        .replace("{", "&lcub;")
        .replace("}", "&rcub;")
        .replace("@", "&commat;")
        .replace("*", "&ast;")
        .replace("/", "&sol;")
        .replace("\\", "&bsol;")
        .replace("#", "&num;")
        .replace("%", "&percnt;")
        .replace("`", "&grave;")
        .replace("^", "&Hat;")
        .replace("+", "&plus;")
        .replace("<", "&lt;")
        .replace("=", "&equals;")
        .replace(">", "&gt;")
        .replace("|", "&vert;")
        .replace("~", "&tilde;")
        .replace("$", "&dollar;")
    )


def safe_xml(value: Any) -> str:
    """
    Encodes unsafe symbols in ``value`` to XML entities and returns the string that can be safely
    used in XML.

    Example::

        safe_xml('<a href="https://circuitpython.org/">CircuitPython</a>')
        # &lt;a href=&quot;https://circuitpython.org/&quot;&gt;CircuitPython&lt;/a&gt;
    """

    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def safe_markdown(value: Any) -> str:
    """
    Encodes unsafe symbols in ``value`` and returns the string that can be safely used in Markdown.

    Example::

        safe_markdown('[CircuitPython](https://circuitpython.org/)')
        # \\[CircuitPython\\]\\(https://circuitpython.org/\\)
    """

    return (
        str(value)
        .replace("_", "\\_")
        .replace("-", "\\-")
        .replace("!", "\\!")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("*", "\\*")
        .replace("*", "\\*")
        .replace("&", "\\&")
        .replace("#", "\\#")
        .replace("`", "\\`")
        .replace("+", "\\+")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("|", "\\|")
        .replace("~", "\\~")
    )


_EXTENDS_PATTERN = re.compile(r"{% extends '.+?' %}|{% extends \".+?\" %}")
_BLOCK_PATTERN = re.compile(r"{% block \w+? %}")
_INCLUDE_PATTERN = re.compile(r"{% include '.+?' %}|{% include \".+?\" %}")
_HASH_COMMENT_PATTERN = re.compile(r"{# .+? #}")
_BLOCK_COMMENT_PATTERN = re.compile(
    r"{% comment ('.*?' |\".*?\" )?%}[\s\S]*?{% endcomment %}"
)
_TOKEN_PATTERN = re.compile(r"{{ .+? }}|{% .+? %}")
_LSTRIP_BLOCK_PATTERN = re.compile(r"\n( )+$")


def _find_extends(template: str):
    return _EXTENDS_PATTERN.search(template)


def _find_block(template: str):
    return _BLOCK_PATTERN.search(template)


def _find_include(template: str):
    return _INCLUDE_PATTERN.search(template)


def _find_named_endblock(template: str, name: str):
    return re.search(r"{% endblock " + name + r" %}", template)


def _exists_and_is_file(path: str) -> bool:
    try:
        return (os.stat(path)[0] & 0b_11110000_00000000) == 0b_10000000_00000000
    except OSError:
        return False


def _resolve_includes(template: str):
    while (include_match := _find_include(template)) is not None:
        template_path = include_match.group(0)[12:-4]

        # TODO: Restrict include to specific directory

        if not _exists_and_is_file(template_path):
            raise OSError(f"Include template not found: {template_path}")

        # Replace the include with the template content
        with open(template_path, "rt", encoding="utf-8") as template_file:
            template = (
                template[: include_match.start()]
                + template_file.read()
                + template[include_match.end() :]
            )
    return template


def _check_for_unsupported_nested_blocks(template: str):
    if _find_block(template) is not None:
        raise ValueError("Nested blocks are not supported")


def _resolve_includes_blocks_and_extends(template: str):
    block_replacements: "dict[str, str]" = {}

    # Processing nested child templates
    while (extends_match := _find_extends(template)) is not None:
        extended_template_name = extends_match.group(0)[12:-4]

        # Load extended template
        with open(
            extended_template_name, "rt", encoding="utf-8"
        ) as extended_template_file:
            extended_template = extended_template_file.read()

        # Removed the extend tag
        template = template[extends_match.end() :]

        # Resolve includes
        template = _resolve_includes(template)

        # Save block replacements
        while (block_match := _find_block(template)) is not None:
            block_name = block_match.group(0)[9:-3]

            endblock_match = _find_named_endblock(template, block_name)

            if endblock_match is None:
                raise ValueError(r"Missing {% endblock %} for block: " + block_name)

            block_content = template[block_match.end() : endblock_match.start()]

            _check_for_unsupported_nested_blocks(block_content)

            if block_name in block_replacements:
                block_replacements[block_name] = block_replacements[block_name].replace(
                    r"{{ block.super }}", block_content
                )
            else:
                block_replacements.setdefault(block_name, block_content)

            template = (
                template[: block_match.start()] + template[endblock_match.end() :]
            )

        template = extended_template

    # Resolve includes in top-level template
    template = _resolve_includes(template)

    return _replace_blocks_with_replacements(template, block_replacements)


def _replace_blocks_with_replacements(template: str, replacements: "dict[str, str]"):
    # Replace blocks in top-level template
    while (block_match := _find_block(template)) is not None:
        block_name = block_match.group(0)[9:-3]

        # Self-closing block tag without default content
        if (endblock_match := _find_named_endblock(template, block_name)) is None:
            replacement = replacements.get(block_name, "")

            template = (
                template[: block_match.start()]
                + replacement
                + template[block_match.end() :]
            )

        # Block with default content
        else:
            block_content = template[block_match.end() : endblock_match.start()]

            _check_for_unsupported_nested_blocks(block_content)

            # No replacement for this block, use default content
            if block_name not in replacements:
                template = (
                    template[: block_match.start()]
                    + block_content
                    + template[endblock_match.end() :]
                )

            # Replace default content with replacement
            else:
                replacement = replacements[block_name].replace(
                    r"{{ block.super }}", block_content
                )

                template = (
                    template[: block_match.start()]
                    + replacement
                    + template[endblock_match.end() :]
                )

    return template


def _find_hash_comment(template: str):
    return _HASH_COMMENT_PATTERN.search(template)


def _find_block_comment(template: str):
    return _BLOCK_COMMENT_PATTERN.search(template)


def _remove_comments(
    template: str,
    *,
    trim_blocks: bool = True,
    lstrip_blocks: bool = True,
):
    def _remove_matched_comment(template: str, comment_match: re.Match):
        text_before_comment = template[: comment_match.start()]
        text_after_comment = template[comment_match.end() :]

        if text_before_comment:
            if lstrip_blocks:
                if _token_is_on_own_line(text_before_comment):
                    text_before_comment = text_before_comment.rstrip(" ")

        if text_after_comment:
            if trim_blocks:
                if text_after_comment.startswith("\n"):
                    text_after_comment = text_after_comment[1:]

        return text_before_comment + text_after_comment

    # Remove hash comments: {# ... #}
    while (comment_match := _find_hash_comment(template)) is not None:
        template = _remove_matched_comment(template, comment_match)

    # Remove block comments: {% comment %} ... {% endcomment %}
    while (comment_match := _find_block_comment(template)) is not None:
        template = _remove_matched_comment(template, comment_match)

    return template


def _find_token(template: str):
    return _TOKEN_PATTERN.search(template)


def _token_is_on_own_line(text_before_token: str) -> bool:
    return _LSTRIP_BLOCK_PATTERN.search(text_before_token) is not None


def _create_template_function(  # pylint: disable=,too-many-locals,too-many-branches,too-many-statements
    template: str,
    language: str = Language.HTML,
    *,
    trim_blocks: bool = True,
    lstrip_blocks: bool = True,
    function_name: str = "_",
    context_name: str = "context",
    dry_run: bool = False,
) -> "Generator[str] | str":
    # Resolve includes, blocks and extends
    template = _resolve_includes_blocks_and_extends(template)

    # Remove comments
    template = _remove_comments(template)

    # Create definition of the template function
    function_string = f"def {function_name}({context_name}):\n"
    indent, indentation_level = "    ", 1

    # Keep track of the template state
    forloop_iterables: "list[str]" = []
    autoescape_modes: "list[bool]" = ["default_on"]
    last_token_was_block = False

    # Resolve tokens
    while (token_match := _find_token(template)) is not None:
        token = token_match.group(0)

        # Add the text before the token
        if text_before_token := template[: token_match.start()]:
            if lstrip_blocks and token.startswith(r"{% "):
                if _token_is_on_own_line(text_before_token):
                    text_before_token = text_before_token.rstrip(" ")

            if trim_blocks:
                if last_token_was_block and text_before_token.startswith("\n"):
                    text_before_token = text_before_token[1:]

            if text_before_token:
                function_string += (
                    indent * indentation_level + f"yield {repr(text_before_token)}\n"
                )

        # Token is an expression
        if token.startswith(r"{{ "):
            last_token_was_block = False

            autoescape = autoescape_modes[-1] in ("on", "default_on")

            # Expression should be escaped with language-specific function
            if autoescape:
                function_string += (
                    indent * indentation_level
                    + f"yield safe_{language.lower()}({token[3:-3]})\n"
                )
            # Expression should not be escaped
            else:
                function_string += (
                    indent * indentation_level + f"yield str({token[3:-3]})\n"
                )

        # Token is a statement
        elif token.startswith(r"{% "):
            last_token_was_block = True

            # Token is a some sort of if statement
            if token.startswith(r"{% if "):
                function_string += indent * indentation_level + f"{token[3:-3]}:\n"
                indentation_level += 1
            elif token.startswith(r"{% elif "):
                indentation_level -= 1
                function_string += indent * indentation_level + f"{token[3:-3]}:\n"
                indentation_level += 1
            elif token == r"{% else %}":
                indentation_level -= 1
                function_string += indent * indentation_level + "else:\n"
                indentation_level += 1
            elif token == r"{% endif %}":
                indentation_level -= 1

            # Token is a for loop
            elif token.startswith(r"{% for "):
                function_string += indent * indentation_level + f"{token[3:-3]}:\n"
                indentation_level += 1

                forloop_iterables.append(token[3:-3].split(" in ", 1)[1])
            elif token == r"{% empty %}":
                indentation_level -= 1

                function_string += (
                    indent * indentation_level + f"if not {forloop_iterables[-1]}:\n"
                )
                indentation_level += 1
            elif token == r"{% endfor %}":
                indentation_level -= 1
                forloop_iterables.pop()

            # Token is a while loop
            elif token.startswith(r"{% while "):
                function_string += indent * indentation_level + f"{token[3:-3]}:\n"
                indentation_level += 1
            elif token == r"{% endwhile %}":
                indentation_level -= 1

            # Token is a Python code
            elif token.startswith(r"{% exec "):
                expression = token[8:-3]
                function_string += indent * indentation_level + f"{expression}\n"

            # Token is autoescape mode change
            elif token.startswith(r"{% autoescape "):
                mode = token[14:-3]
                if mode not in ("on", "off"):
                    raise ValueError(f"Unknown autoescape mode: {mode}")
                autoescape_modes.append(mode)
            elif token == r"{% endautoescape %}":
                if autoescape_modes == ["default_on"]:
                    raise ValueError("No autoescape mode to end")
                autoescape_modes.pop()

            else:
                raise ValueError(
                    f"Unknown token type: {token} at {token_match.start()}"
                )

        else:
            raise ValueError(f"Unknown token type: {token} at {token_match.start()}")

        # Continue with the rest of the template
        template = template[token_match.end() :]

    # Add the text after the last token (if any)
    text_after_last_token = template

    if text_after_last_token:
        if trim_blocks and text_after_last_token.startswith("\n"):
            text_after_last_token = text_after_last_token[1:]

        function_string += (
            indent * indentation_level + f"yield {repr(text_after_last_token)}\n"
        )

    # If dry run, return the template function string
    if dry_run:
        return function_string

    # Create and return the template function
    exec(function_string)  # pylint: disable=exec-used
    return locals()[function_name]


def _yield_as_sized_chunks(
    generator: "Generator[str]", chunk_size: int
) -> "Generator[str]":
    """Yields resized chunks from the ``generator``."""

    # Yield chunks with a given size
    chunk = ""
    for item in generator:
        chunk += item

        if chunk_size <= len(chunk):
            yield chunk[:chunk_size]
            chunk = chunk[chunk_size:]

    # Yield the last chunk
    if chunk:
        yield chunk


class Template:
    """
    Class that loads a template from ``str`` and allows to rendering it with different contexts.
    """

    _template_function: "Generator[str]"

    def __init__(self, template_string: str, *, language: str = Language.HTML) -> None:
        """
        Creates a reusable template from the given template string.

        For better performance, instantiate the template in global scope and reuse it as many times.
        If memory is a concern, instantiate the template in a function or method that uses it.

        By default, the template is rendered as HTML. To render it as XML or Markdown, use the
        ``language`` parameter.

        :param str template_string: String containing the template to be rendered
        :param str language: Language for autoescaping. Defaults to HTML
        """
        self._template_function = _create_template_function(template_string, language)

    def render_iter(
        self, context: dict = None, *, chunk_size: int = None
    ) -> "Generator[str]":
        """
        Renders the template using the provided context and returns a generator that yields the
        rendered output.

        :param dict context: Dictionary containing the context for the template
        :param int chunk_size: Size of the chunks to be yielded. If ``None``, the generator yields
            the template in chunks sized specifically for the given template

        Example::

            template = ... # r"Hello {{ name }}!"

            list(template.render_iter({"name": "World"}))
            # ['Hello ', 'World', '!']

            list(template.render_iter({"name": "CircuitPython"}, chunk_size=3))
            # ['Hel', 'lo ', 'Cir', 'cui', 'tPy', 'tho', 'n!']
        """
        return (
            _yield_as_sized_chunks(self._template_function(context or {}), chunk_size)
            if chunk_size is not None
            else self._template_function(context or {})
        )

    def render(self, context: dict = None) -> str:
        """
        Render the template with the given context.

        :param dict context: Dictionary containing the context for the template

        Example::

            template = ... # r"Hello {{ name }}!"

            template.render({"name": "World"})
            # 'Hello World!'
        """
        return "".join(self.render_iter(context or {}))


class FileTemplate(Template):
    """
    Class that loads a template from a file and allows to rendering it with different contexts.
    """

    def __init__(self, template_path: str, *, language: str = Language.HTML) -> None:
        """
        Loads a file and creates a reusable template from its contents.

        For better performance, instantiate the template in global scope and reuse it as many times.
        If memory is a concern, instantiate the template in a function or method that uses it.

        By default, the template is rendered as HTML. To render it as XML or Markdown, use the
        ``language`` parameter.

        :param str template_path: Path to a file containing the template to be rendered
        :param str language: Language for autoescaping. Defaults to HTML
        """
        with open(template_path, "rt", encoding="utf-8") as template_file:
            template_string = template_file.read()
        super().__init__(template_string, language=language)


def render_string_iter(
    template_string: str,
    context: dict = None,
    *,
    chunk_size: int = None,
    language: str = Language.HTML,
):
    """
    Creates a `Template` from the given ``template_string`` and renders it using the provided
    ``context``. Returns a generator that yields the rendered output.

    :param dict context: Dictionary containing the context for the template
    :param int chunk_size: Size of the chunks to be yielded. If ``None``, the generator yields
        the template in chunks sized specifically for the given template
    :param str language: Language for autoescaping. Defaults to HTML

    Example::

        list(render_string_iter(r"Hello {{ name }}!", {"name": "World"}))
        # ['Hello ', 'World', '!']

        list(render_string_iter(r"Hello {{ name }}!", {"name": "CircuitPython"}, chunk_size=3))
        # ['Hel', 'lo ', 'Cir', 'cui', 'tPy', 'tho', 'n!']
    """
    return Template(template_string, language=language).render_iter(
        context or {}, chunk_size=chunk_size
    )


def render_string(
    template_string: str,
    context: dict = None,
    *,
    language: str = Language.HTML,
):
    """
    Creates a `Template` from the given ``template_string`` and renders it using the provided
    ``context``. Returns the rendered output as a string.

    :param dict context: Dictionary containing the context for the template
    :param str language: Language for autoescaping. Defaults to HTML

    Example::

        render_string(r"Hello {{ name }}!", {"name": "World"})
        # 'Hello World!'
    """
    return Template(template_string, language=language).render(context or {})


def render_template_iter(
    template_path: str,
    context: dict = None,
    *,
    chunk_size: int = None,
    language: str = Language.HTML,
):
    """
    Creates a `FileTemplate` from the given ``template_path`` and renders it using the provided
    ``context``. Returns a generator that yields the rendered output.

    :param dict context: Dictionary containing the context for the template
    :param int chunk_size: Size of the chunks to be yielded. If ``None``, the generator yields
        the template in chunks sized specifically for the given template
    :param str language: Language for autoescaping. Defaults to HTML

    Example::

        list(render_template_iter(..., {"name": "World"})) # r"Hello {{ name }}!"
        # ['Hello ', 'World', '!']

        list(render_template_iter(..., {"name": "CircuitPython"}, chunk_size=3))
        # ['Hel', 'lo ', 'Cir', 'cui', 'tPy', 'tho', 'n!']
    """
    return FileTemplate(template_path, language=language).render_iter(
        context or {}, chunk_size=chunk_size
    )


def render_template(
    template_path: str,
    context: dict = None,
    *,
    language: str = Language.HTML,
):
    """
    Creates a `FileTemplate` from the given ``template_path`` and renders it using the provided
    ``context``. Returns the rendered output as a string.

    :param dict context: Dictionary containing the context for the template
    :param str language: Language for autoescaping. Defaults to HTML

    Example::

        render_template(..., {"name": "World"}) # r"Hello {{ name }}!"
        # 'Hello World!'
    """
    return FileTemplate(template_path, language=language).render(context or {})
