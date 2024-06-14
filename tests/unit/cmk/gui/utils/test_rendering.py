#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.html import HTML
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html


@pytest.mark.parametrize(
    "elements, separator, rendered_title",
    [
        (
            [],
            None,
            HTML.empty(),
        ),
        (
            [("element", None)],
            None,
            HTML.without_escaping("element"),
        ),
        (
            [("element", "link")],
            None,
            HTML.without_escaping('<a href="link" title="element">element</a>'),
        ),
        (
            [("element1", "link1"), ("element2", None), ("element3", "link3")],
            HTML.empty(),
            HTML.without_escaping(
                '<a href="link1" title="element1">element1</a>element2<a href="link3" title="element3">element3</a>'
            ),
        ),
        (
            [("element1", "link1"), ("element2", None), ("element3", "link3")],
            HTML.without_escaping(" / "),
            HTML.without_escaping(
                '<a href="link1" title="element1">element1</a> / element2 / <a href="link3" title="element3">element3</a>'
            ),
        ),
    ],
)
def test_text_with_links_to_user_translated_html(
    request_context: None,
    elements: list[tuple[str, str | None]],
    separator: HTML | None,
    rendered_title: HTML,
) -> None:
    assert (
        text_with_links_to_user_translated_html(
            elements,
            separator=separator,
        )
        == rendered_title
    )
