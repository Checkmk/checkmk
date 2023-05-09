#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
            "",
            HTML(""),
        ),
        (
            [("element", None)],
            "",
            HTML("element"),
        ),
        (
            [("element", "link")],
            "",
            HTML("<a href=\"link\">element</a>"),
        ),
        (
            [("element1", "link1"), ("element2", None), ("element3", "link3")],
            "",
            HTML("<a href=\"link1\">element1</a>element2<a href=\"link3\">element3</a>"),
        ),
        (
            [("element1", "link1"), ("element2", None), ("element3", "link3")],
            " / ",
            HTML("<a href=\"link1\">element1</a> / element2 / <a href=\"link3\">element3</a>"),
        ),
    ],
)
def test_text_with_links_to_user_translated_html(
    module_wide_request_context,
    elements,
    separator,
    rendered_title,
):
    assert text_with_links_to_user_translated_html(
        elements,
        separator=separator,
    ) == rendered_title
