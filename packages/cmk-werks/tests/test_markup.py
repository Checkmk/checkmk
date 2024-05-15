#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.werks.markup import markdown_to_nowiki


def test_markdown_with_arbitrary_nested_tags() -> None:
    assert (
        markdown_to_nowiki(
            "<p>description with <tt>nested <b>formatting</b></tt> and other <i>i</i> b</p>"
        )
        == "description with <tt>nested <b>formatting</b></tt> and other <i>i</i> b\n"
    )


def test_markdown_with_unknown_root_tag() -> None:
    # unknown html should be passed along, both markdown and nowiki support plain html
    table = "<table><tr><td>td</td></tr></table>"
    assert markdown_to_nowiki(table) == table
