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


class Token:  # pylint: disable=too-few-public-methods
    """Stores a token with its position in a template."""

    def __init__(self, template: str, start_position: int, end_position: int):
        self.template = template
        self.start_position = start_position
        self.end_position = end_position

        self.content = template[start_position:end_position]


class TemplateNotFoundError(OSError):
    """Raised when a template file is not found."""

    def __init__(self, path: str):
        """Specified template file that was not found."""
        super().__init__(f"Template file not found: {path}")


class TemplateSyntaxError(SyntaxError):
    """Raised when a syntax error is encountered in a template."""

    def __init__(self, token: Token, reason: str):
        """Provided token is not a valid template syntax at the specified position."""
        super().__init__(self._underline_token_in_template(token) + f"\n\n{reason}")

    @staticmethod
    def _skipped_lines_message(nr_of_lines: int) -> str:
        return f"[{nr_of_lines} line{'s' if nr_of_lines > 1 else ''} skipped]"

    @classmethod
    def _underline_token_in_template(
        cls, token: Token, *, lines_around: int = 4, symbol: str = "^"
    ) -> str:
        """
        Return ``number_of_lines`` lines before and after ``token``, with the token content
        underlined with ``symbol`` e.g.:

        ```html
        [8 lines skipped]
                Shopping list:
                <ul>
                    {% for item in context["items"] %}
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                        <li>{{ item["name"] }} - ${{ item["price"] }}</li>
                    {% empty %}
        [5 lines skipped]
        ```
        """

        template_before_token = token.template[: token.start_position]
        if skipped_lines := template_before_token.count("\n") - lines_around:
            template_before_token = (
                f"{cls._skipped_lines_message(skipped_lines)}\n"
                + "\n".join(template_before_token.split("\n")[-(lines_around + 1) :])
            )

        template_after_token = token.template[token.end_position :]
        if skipped_lines := template_after_token.count("\n") - lines_around:
            template_after_token = (
                "\n".join(template_after_token.split("\n")[: (lines_around + 1)])
                + f"\n{cls._skipped_lines_message(skipped_lines)}"
            )

        lines_before_line_with_token = template_before_token.rsplit("\n", 1)[0]

        line_with_token = (
            template_before_token.rsplit("\n", 1)[-1]
            + token.content
            + template_after_token.split("\n")[0]
        )

        line_with_underline = (
            " " * len(template_before_token.rsplit("\n", 1)[-1])
            + symbol * len(token.content)
            + " " * len(template_after_token.split("\n")[0])
        )

        lines_after_line_with_token = template_after_token.split("\n", 1)[-1]

        return "\n".join(
            [
                lines_before_line_with_token,
                line_with_token,
                line_with_underline,
                lines_after_line_with_token,
            ]
        )


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


def _find_any_non_whitespace(template: str):
    return re.search(r"\S+", template)


def _find_endblock(template: str, name: str = r"\w+?"):
    return re.search(r"{% endblock " + name + r" %}", template)


def _find_include(template: str):
    return _INCLUDE_PATTERN.search(template)


def _find_hash_comment(template: str):
    return _HASH_COMMENT_PATTERN.search(template)


def _find_block_comment(template: str):
    return _BLOCK_COMMENT_PATTERN.search(template)


def _find_token(template: str):
    return _TOKEN_PATTERN.search(template)


def _token_is_on_own_line(text_before_token: str) -> bool:
    return _LSTRIP_BLOCK_PATTERN.search(text_before_token) is not None


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
            raise TemplateNotFoundError(template_path)

        # Replace the include with the template content
        with open(template_path, "rt", encoding="utf-8") as template_file:
            template = (
                template[: include_match.start()]
                + template_file.read()
                + template[include_match.end() :]
            )
    return template


def _resolve_includes_blocks_and_extends(  # pylint: disable=,too-many-locals
    template: str,
):
    extended_templates: "set[str]" = set()
    block_replacements: "dict[str, str]" = {}

    # Processing nested child templates
    while (extends_match := _find_extends(template)) is not None:
        extended_template_path = extends_match.group(0)[12:-4]

        if not _exists_and_is_file(extended_template_path):
            raise TemplateNotFoundError(extended_template_path)

        # Check for circular extends
        if extended_template_path in extended_templates:
            raise TemplateSyntaxError(
                Token(
                    template,
                    extends_match.start(),
                    extends_match.end(),
                ),
                "Circular extends",
            )

        # Load extended template
        extended_templates.add(extended_template_path)
        with open(
            extended_template_path, "rt", encoding="utf-8"
        ) as extended_template_file:
            extended_template = extended_template_file.read()

        offset = extends_match.end()

        # Resolve includes
        template = _resolve_includes(template)

        # Check for any stacked extends
        if stacked_extends_match := _find_extends(template[extends_match.end() :]):
            raise TemplateSyntaxError(
                Token(
                    template,
                    extends_match.end() + stacked_extends_match.start(),
                    extends_match.end() + stacked_extends_match.end(),
                ),
                "Incorrect use of {% extends ... %}",
            )

        # Save block replacements
        while (block_match := _find_block(template[offset:])) is not None:
            block_name = block_match.group(0)[9:-3]

            # Check for anything between blocks
            if content_between_blocks := _find_any_non_whitespace(
                template[offset : offset + block_match.start()]
            ):
                raise TemplateSyntaxError(
                    Token(
                        template,
                        offset + content_between_blocks.start(),
                        offset + content_between_blocks.end(),
                    ),
                    "Content outside block",
                )

            if not (endblock_match := _find_endblock(template[offset:], block_name)):
                raise TemplateSyntaxError(
                    Token(
                        template,
                        offset + block_match.start(),
                        offset + block_match.end(),
                    ),
                    "No matching {% endblock %}",
                )

            block_content = template[
                offset + block_match.end() : offset + endblock_match.start()
            ]

            # Check for unsupported nested blocks
            if (nested_block_match := _find_block(block_content)) is not None:
                raise TemplateSyntaxError(
                    Token(
                        template,
                        offset + block_match.end() + nested_block_match.start(),
                        offset + block_match.end() + nested_block_match.end(),
                    ),
                    "Nested blocks are not supported",
                )

            if block_name in block_replacements:
                block_replacements[block_name] = block_replacements[block_name].replace(
                    r"{{ block.super }}", block_content
                )
            else:
                block_replacements.setdefault(block_name, block_content)

            offset += endblock_match.end()

        if content_after_last_endblock := _find_any_non_whitespace(template[offset:]):
            raise TemplateSyntaxError(
                Token(
                    template,
                    offset + content_after_last_endblock.start(),
                    offset + content_after_last_endblock.end(),
                ),
                "Content outside block",
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
        if (endblock_match := _find_endblock(template, block_name)) is None:
            replacement = replacements.get(block_name, "")

            template = (
                template[: block_match.start()]
                + replacement
                + template[block_match.end() :]
            )

        # Block with default content
        else:
            block_content = template[block_match.end() : endblock_match.start()]

            # Check for unsupported nested blocks
            if (nested_block_match := _find_block(block_content)) is not None:
                raise TemplateSyntaxError(
                    Token(
                        template,
                        block_match.end() + nested_block_match.start(),
                        block_match.end() + nested_block_match.end(),
                    ),
                    "Nested blocks are not supported",
                )

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


def _create_template_rendering_function(  # pylint: disable=,too-many-locals,too-many-branches,too-many-statements
    template: str,
    *,
    trim_blocks: bool = True,
    lstrip_blocks: bool = True,
    function_name: str = "__template_rendering_function",
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
    nested_if_statements: "list[Token]" = []
    nested_for_loops: "list[Token]" = []
    nested_while_loops: "list[Token]" = []
    nested_autoescape_modes: "list[Token]" = []
    last_token_was_block = False
    offset = 0

    # Resolve tokens
    while (token_match := _find_token(template[offset:])) is not None:
        token = Token(
            template,
            offset + token_match.start(),
            offset + token_match.end(),
        )

        # Add the text before the token
        if text_before_token := template[offset : offset + token_match.start()]:
            if lstrip_blocks and token.content.startswith(r"{% "):
                if _token_is_on_own_line(text_before_token):
                    text_before_token = text_before_token.rstrip(" ")

            if trim_blocks:
                if last_token_was_block and text_before_token.startswith("\n"):
                    text_before_token = text_before_token[1:]

        if text_before_token:
            function_string += (
                indent * indentation_level + f"yield {repr(text_before_token)}\n"
            )
        else:
            function_string += indent * indentation_level + "pass\n"

        # Token is an expression
        if token.content.startswith(r"{{ "):
            last_token_was_block = False

            if nested_autoescape_modes:
                autoescape = nested_autoescape_modes[-1].content[14:-3] == "on"
            else:
                autoescape = True

            # Expression should be escaped
            if autoescape:
                function_string += (
                    indent * indentation_level
                    + f"yield safe_html({token.content[3:-3]})\n"
                )
            # Expression should not be escaped
            else:
                function_string += (
                    indent * indentation_level + f"yield str({token.content[3:-3]})\n"
                )

        # Token is a statement
        elif token.content.startswith(r"{% "):
            last_token_was_block = True

            # Token is a some sort of if statement
            if token.content.startswith(r"{% if "):
                function_string += (
                    indent * indentation_level + f"{token.content[3:-3]}:\n"
                )
                indentation_level += 1

                nested_if_statements.append(token)
            elif token.content.startswith(r"{% elif "):
                if not nested_if_statements:
                    raise TemplateSyntaxError(token, "No matching {% if ... %}")

                indentation_level -= 1
                function_string += (
                    indent * indentation_level + f"{token.content[3:-3]}:\n"
                )
                indentation_level += 1
            elif token.content == r"{% else %}":
                if not nested_if_statements:
                    raise TemplateSyntaxError(token, "No matching {% if ... %}")

                indentation_level -= 1
                function_string += indent * indentation_level + "else:\n"
                indentation_level += 1
            elif token.content == r"{% endif %}":
                if not nested_if_statements:
                    raise TemplateSyntaxError(token, "No matching {% if ... %}")

                indentation_level -= 1
                nested_if_statements.pop()

            # Token is a for loop
            elif token.content.startswith(r"{% for "):
                function_string += (
                    indent * indentation_level + f"{token.content[3:-3]}:\n"
                )
                indentation_level += 1

                nested_for_loops.append(token)
            elif token.content == r"{% empty %}":
                if not nested_for_loops:
                    raise TemplateSyntaxError(token, "No matching {% for ... %}")

                indentation_level -= 1
                last_forloop_iterable = (
                    nested_for_loops[-1].content[3:-3].split(" in ", 1)[1]
                )
                function_string += (
                    indent * indentation_level + f"if not {last_forloop_iterable}:\n"
                )
                indentation_level += 1
            elif token.content == r"{% endfor %}":
                if not nested_for_loops:
                    raise TemplateSyntaxError(token, "No matching {% for ... %}")

                indentation_level -= 1
                nested_for_loops.pop()

            # Token is a while loop
            elif token.content.startswith(r"{% while "):
                function_string += (
                    indent * indentation_level + f"{token.content[3:-3]}:\n"
                )
                indentation_level += 1

                nested_while_loops.append(token)
            elif token.content == r"{% endwhile %}":
                if not nested_while_loops:
                    raise TemplateSyntaxError(token, "No matching {% while ... %}")

                indentation_level -= 1
                nested_while_loops.pop()

            # Token is a Python code
            elif token.content.startswith(r"{% exec "):
                expression = token.content[8:-3]
                function_string += indent * indentation_level + f"{expression}\n"

            # Token is a autoescape mode change
            elif token.content.startswith(r"{% autoescape "):
                mode = token.content[14:-3]
                if mode not in ("on", "off"):
                    raise ValueError(f"Unknown autoescape mode: {mode}")

                nested_autoescape_modes.append(token)

            elif token.content == r"{% endautoescape %}":
                if not nested_autoescape_modes:
                    raise TemplateSyntaxError(token, "No matching {% autoescape ... %}")

                nested_autoescape_modes.pop()

            # Token is a endblock in top-level template
            elif token.content.startswith(r"{% endblock "):
                raise TemplateSyntaxError(token, "No matching {% block ... %}")

            # Token is a extends in top-level template
            elif token.content.startswith(r"{% extends "):
                raise TemplateSyntaxError(token, "Incorrect use of {% extends ... %}")

            else:
                raise TemplateSyntaxError(token, f"Unknown token: {token.content}")

        else:
            raise TemplateSyntaxError(token, f"Unknown token: {token.content}")

        # Move offset to the end of the token
        offset += token_match.end()

    # Checking for unclosed blocks
    if len(nested_if_statements) > 0:
        last_if_statement = nested_if_statements[-1]
        raise TemplateSyntaxError(last_if_statement, "No matching {% endif %}")

    if len(nested_for_loops) > 0:
        last_for_loop = nested_for_loops[-1]
        raise TemplateSyntaxError(last_for_loop, "No matching {% endfor %}")

    if len(nested_while_loops) > 0:
        last_while_loop = nested_while_loops[-1]
        raise TemplateSyntaxError(last_while_loop, "No matching {% endwhile %}")

    # No check for unclosed autoescape blocks, as they are optional and do not result in errors

    # Add the text after the last token (if any)
    text_after_last_token = template[offset:]

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

    def __init__(self, template_string: str) -> None:
        """
        Creates a reusable template from the given template string.

        :param str template_string: String containing the template to be rendered
        """
        self._template_function = _create_template_rendering_function(template_string)

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

    def __init__(self, template_path: str) -> None:
        """
        Loads a file and creates a reusable template from its contents.

        :param str template_path: Path to a file containing the template to be rendered
        """

        if not _exists_and_is_file(template_path):
            raise TemplateNotFoundError(template_path)

        with open(template_path, "rt", encoding="utf-8") as template_file:
            template_string = template_file.read()
        super().__init__(template_string)


_CACHE: "dict[int, Template| FileTemplate]" = {}


def render_string_iter(
    template_string: str,
    context: dict = None,
    *,
    chunk_size: int = None,
    cache: bool = True,
):
    """
    Creates a `Template` from the given ``template_string`` and renders it using the provided
    ``context``. Returns a generator that yields the rendered output.

    If ``cache`` is ``True``, the template is saved and reused on next calls, even with different
    contexts.

    :param dict context: Dictionary containing the context for the template
    :param int chunk_size: Size of the chunks to be yielded. If ``None``, the generator yields
        the template in chunks sized specifically for the given template
    :param bool cache: When ``True``, the template is saved and reused on next calls.

    Example::

        list(render_string_iter(r"Hello {{ name }}!", {"name": "World"}))
        # ['Hello ', 'World', '!']

        list(render_string_iter(r"Hello {{ name }}!", {"name": "CircuitPython"}, chunk_size=3))
        # ['Hel', 'lo ', 'Cir', 'cui', 'tPy', 'tho', 'n!']
    """
    key = hash(template_string)

    if cache and key in _CACHE:
        return _yield_as_sized_chunks(
            _CACHE[key].render_iter(context or {}, chunk_size), chunk_size
        )

    template = Template(template_string)

    if cache:
        _CACHE[key] = template

    return _yield_as_sized_chunks(
        template.render_iter(context or {}), chunk_size=chunk_size
    )


def render_string(
    template_string: str,
    context: dict = None,
    *,
    cache: bool = True,
):
    """
    Creates a `Template` from the given ``template_string`` and renders it using the provided
    ``context``. Returns the rendered output as a string.

    If ``cache`` is ``True``, the template is saved and reused on next calls, even with different
    contexts.

    :param dict context: Dictionary containing the context for the template
    :param bool cache: When ``True``, the template is saved and reused on next calls.

    Example::

        render_string(r"Hello {{ name }}!", {"name": "World"})
        # 'Hello World!'
    """
    key = hash(template_string)

    if cache and key in _CACHE:
        return _CACHE[key].render(context or {})

    template = Template(template_string)

    if cache:
        _CACHE[key] = template

    return template.render(context or {})


def render_template_iter(
    template_path: str,
    context: dict = None,
    *,
    chunk_size: int = None,
    cache: bool = True,
):
    """
    Creates a `FileTemplate` from the given ``template_path`` and renders it using the provided
    ``context``. Returns a generator that yields the rendered output.

    If ``cache`` is ``True``, the template is saved and reused on next calls, even with different
    contexts.

    :param dict context: Dictionary containing the context for the template
    :param int chunk_size: Size of the chunks to be yielded. If ``None``, the generator yields
        the template in chunks sized specifically for the given template
    :param bool cache: When ``True``, the template is saved and reused on next calls.

    Example::

        list(render_template_iter(..., {"name": "World"})) # r"Hello {{ name }}!"
        # ['Hello ', 'World', '!']

        list(render_template_iter(..., {"name": "CircuitPython"}, chunk_size=3))
        # ['Hel', 'lo ', 'Cir', 'cui', 'tPy', 'tho', 'n!']
    """
    key = hash(template_path)

    if cache and key in _CACHE:
        return _yield_as_sized_chunks(
            _CACHE[key].render_iter(context or {}, chunk_size), chunk_size
        )

    template = FileTemplate(template_path)

    if cache:
        _CACHE[key] = template

    return _yield_as_sized_chunks(
        template.render_iter(context or {}, chunk_size=chunk_size), chunk_size
    )


def render_template(
    template_path: str,
    context: dict = None,
    *,
    cache: bool = True,
):
    """
    Creates a `FileTemplate` from the given ``template_path`` and renders it using the provided
    ``context``. Returns the rendered output as a string.

    If ``cache`` is ``True``, the template is saved and reused on next calls, even with different
    contexts.

    :param dict context: Dictionary containing the context for the template
    :param bool cache: When ``True``, the template is saved and reused on next calls.

    Example::

        render_template(..., {"name": "World"}) # r"Hello {{ name }}!"
        # 'Hello World!'
    """

    key = hash(template_path)

    if cache and key in _CACHE:
        return _CACHE[key].render(context or {})

    template = FileTemplate(template_path)

    if cache:
        _CACHE[key] = template

    return template.render(context or {})
