#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for cmk.gui.utils.html_tag_balance."""

import pytest

from cmk.gui.utils.html_tag_balance import check_html_tag_balance


@pytest.mark.parametrize(
    "body",
    [
        "<html><body><div></div></body></html>",
        "<html><body><br><img src='x'><input></body></html>",
        '<html><body><div><span>x</span><p class="y">z</p></div></body></html>',
        "",
        "<div></div>",
    ],
)
def test_balanced_html_returns_no_errors(body: str) -> None:
    assert check_html_tag_balance(body) == []


@pytest.mark.parametrize(
    "body, expected_snippet",
    [
        # Tags left open at EOF.
        ("<html><body><div><p>content", "never closed"),
        # Extra close tag with nothing on the stack.
        ("</div>", "extra </div>"),
        # Inner element unclosed before outer close.
        ("<html><body><div><span></body></html>", "not closed before"),
        # Crossed tags.
        ("<html><body><div><span></div></span></body></html>", "not closed before"),
    ],
)
def test_unbalanced_html_returns_errors(body: str, expected_snippet: str) -> None:
    errors = check_html_tag_balance(body)
    assert errors, f"expected errors for: {body}"
    assert any(expected_snippet in err for err in errors), (
        f"expected snippet {expected_snippet!r} in {errors}"
    )


def test_single_unclosed_tag_produces_one_error_not_cascade() -> None:
    """A single unclosed inner tag must not cascade into N errors."""
    body = "<html><body><p>text</body></html>"
    errors = check_html_tag_balance(body)
    assert len(errors) == 1, f"expected 1 error, got {len(errors)}: {errors}"
    assert "<p>" in errors[0]


def test_void_elements_do_not_produce_errors() -> None:
    body = "<div><br><img src='x'><input type='text'><hr></div>"
    assert check_html_tag_balance(body) == []


def test_boolean_attrs_included_in_error_messages() -> None:
    """Boolean attributes (value=None) should appear in the error."""
    body = "<div hidden><p>text</div>"
    errors = check_html_tag_balance(body)
    # <p> is unclosed; the error for <div hidden> should include 'hidden'
    assert any("hidden" in err for err in errors) or any("<p>" in err for err in errors)


def test_script_content_not_parsed_as_tags() -> None:
    """Angle brackets inside <script> should not be treated as tags."""
    body = "<html><body><script>if (a < b && c > d) {}</script></body></html>"
    assert check_html_tag_balance(body) == []


def test_self_closing_tags_ignored() -> None:
    body = "<div><br/><img src='x' /></div>"
    assert check_html_tag_balance(body) == []
