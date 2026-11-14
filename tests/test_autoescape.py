# SPDX-FileCopyrightText: Copyright (c) 2026 Shantanu
#
# SPDX-License-Identifier: MIT

from adafruit_templateengine import render_string


def test_autoescape_off_renders_integer_context_values_as_strings():
    template = '{% autoescape off %}number = {{ context["number"] }}{% endautoescape %}'

    assert render_string(template, {"number": 19}, cache=False) == "number = 19"
