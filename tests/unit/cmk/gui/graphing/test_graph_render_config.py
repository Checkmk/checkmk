#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._graph_render_config import GraphRenderOptions, GraphTitleFormat


def test_from_graph_render_options_vs_empty_title_format() -> None:
    # Crash group 4324: no title element was selected, stored as an empty list
    assert GraphRenderOptions.from_graph_render_options_vs(
        {"title_format": []}
    ).title_format == GraphTitleFormat(
        plain=False,
        add_host_name=False,
        add_host_alias=False,
        add_service_description=False,
    )
