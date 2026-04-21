#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from scripts.html_validation.lib.tag_balance import check_html_tag_balance, TagImbalanceError


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "<html><body><div></div></body></html>",
            id="Simple document with normal elements",
        ),
        pytest.param(
            "<html><body><div><span>x</span><p class='y'>z</p></div></body></html>",
            id="Simple document with normal elements and attributes",
        ),
        pytest.param(
            "<div><br><img src='x'><input type='text'><hr></div>",
            id="Void elements do not produce errors.",
        ),
        pytest.param(
            "<html><body><script>if (a < b && c > d) {}</script></body></html>",
            id="Angle brackets inside <script> should not be treated as tags.",
        ),
        pytest.param(
            "<div><br/><img src='x' /></div>",
            id="Self closing tags ignored.",
        ),
    ],
)
def test_check_html_tag_balance_success(body: str) -> None:
    assert check_html_tag_balance(body)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "<html><body><div><p>content",
            id="Tags left open at EOF.",
        ),
        pytest.param(
            "</div>",
            id="Extra close tag with nothing on the stack.",
        ),
        pytest.param(
            "<html><body><div><span></body></html>",
            id="Inner element unclosed before outer close.",
        ),
        pytest.param(
            "<html><body><div><span></div></span></body></html>",
            id="Crossed tags - mismatches between open and closed tags.",
        ),
        pytest.param(
            "<html><body><div><span></div></span></body></html>",
            id="A single unclosed inner tag must not cascade into N errors.",
        ),
        pytest.param(
            "<html><body><div><span></div></span></body></html>",
            id="Boolean attributes (value=None) should appear in the error.",
        ),
    ],
)
def test_check_html_tag_balance_errors(body: str) -> None:
    with pytest.raises(TagImbalanceError):
        check_html_tag_balance(body)


def test_check_html_tag_balance_error_payload() -> None:
    imbalanced_html = """
    <html>
        <main id="content">
            <div class="card">
                <a href="/">Home</a>
                </span>
    </html>
    """

    try:
        check_html_tag_balance(imbalanced_html)
    except TagImbalanceError as exc:
        value = exc.get_errors()
        expected = {
            "count": 3,
            "errors": [
                {
                    "line": 3,
                    "reason": "not closed before </html>",
                    "tag": "<main id='content'>",
                },
                {
                    "line": 4,
                    "reason": "not closed before </html>",
                    "tag": "<div class='card'>",
                },
                {
                    "line": 6,
                    "reason": "has no matching open tag",
                    "tag": "</span",
                },
            ],
        }
        assert value == expected
