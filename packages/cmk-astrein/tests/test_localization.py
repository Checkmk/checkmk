#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

import pytest

from cmk.astrein.checker_localization import LocalizationChecker


@pytest.mark.parametrize(
    ["code", "is_error"],
    [
        pytest.param("_('abc')", False, id="literal_string_ok"),
        pytest.param("_(x)", True, id="variable_not_allowed"),
        pytest.param("_l('%s' % '123')", True, id="string_formatting_not_allowed"),
        pytest.param("_l('%s text')", False, id="literal_with_format_placeholder_ok"),
        pytest.param("_l('{argl} text')", False, id="literal_with_format_braces_ok"),
        pytest.param("_(f'{argl} text')", True, id="fstring_not_allowed"),
    ],
)
def test_literal_string_checker(
    code: str,
    is_error: bool,
) -> None:
    """Test that localization functions must be called with literal strings."""
    checker = LocalizationChecker(Path("test/test.py"), Path("test"), code)
    tree = ast.parse(code)
    errors = checker.check(tree)

    if is_error:
        assert len(errors) > 0, f"Expected error for: {code}"
        assert "non-literal string" in errors[0].message
    else:
        assert len(errors) == 0, f"Unexpected error for: {code}"


@pytest.mark.parametrize(
    ["code", "is_error"],
    [
        pytest.param("_('abc')", False, id="no_html_ok"),
        pytest.param("_l('<tt>bold</tt>')", False, id="allowed_tag_ok"),
        pytest.param("_('* ? <a href=\"%s\">%s</a>')", False, id="link_allowed"),
        pytest.param(
            '_(\'&copy; <a target="_blank" href="https://checkmk.com">Checkmk GmbH</a>\')',
            False,
            id="link_with_target_ok",
        ),
        pytest.param(
            "_('123 <script>injection</script>')",
            True,
            id="script_tag_forbidden",
        ),
    ],
)
def test_html_tags_checker(
    code: str,
    is_error: bool,
) -> None:
    """Test that HTML tags in localization strings must be from allowed set."""
    checker = LocalizationChecker(Path("test/test.py"), Path("test"), code)
    tree = ast.parse(code)
    errors = checker.check(tree)

    if is_error:
        assert len(errors) > 0, f"Expected error for: {code}"
        assert "forbidden HTML tags" in errors[0].message
    else:
        assert len(errors) == 0, f"Unexpected error for: {code}"


def test_multiple_errors() -> None:
    """Test that multiple errors can be detected in one file."""
    code = """
_('valid string')
_(variable)
_l('<script>bad</script>')
_('another valid string')
"""
    checker = LocalizationChecker(Path("test/test.py"), Path("test"), code)
    tree = ast.parse(code)
    errors = checker.check(tree)

    # Should find 2 errors: variable usage and forbidden HTML tag
    assert len(errors) == 2


def test_non_translation_function() -> None:
    """Test that non-translation functions are ignored."""
    code = """
print(variable)
some_function(x)
"""
    checker = LocalizationChecker(Path("test/test.py"), Path("test"), code)
    tree = ast.parse(code)
    errors = checker.check(tree)

    assert len(errors) == 0


def test_all_translation_functions() -> None:
    """Test that all translation function names are checked."""
    translation_functions = [
        "_",
        "_l",
        "gettext",
        "Title",
        "Help",
        "Label",
        "Message",
    ]

    for func_name in translation_functions:
        code = f"{func_name}(variable)"
        checker = LocalizationChecker(Path("test/test.py"), Path("test"), code)
        tree = ast.parse(code)
        errors = checker.check(tree)

        assert len(errors) > 0, f"Expected error for translation function: {func_name}"
        assert "non-literal string" in errors[0].message
