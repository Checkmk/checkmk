#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.gui.plugins.dashboard.event_bar_chart_dashlet import bar_chart_title


@pytest.mark.parametrize(
    "properties, settings, result",
    [
        pytest.param(
            {"log_target": "both"},
            {
                "show_title": False,
                "title": "title",
                "type": "notifications_bar_chart",
                "single_infos": [],
            },
            "",
            id="no show title",
        ),
        pytest.param(
            {"log_target": "both"},
            {
                "show_title": True,
                "type": "notifications_bar_chart",
                "single_infos": [],
            },
            "Host and service notifications",
            id="default title",
        ),
        pytest.param(
            {"log_target": "both"},
            {
                "show_title": True,
                "type": "notifications_bar_chart",
                "single_infos": [],
                "title": "fancy title / $GRAPH_TITLE$",
            },
            "fancy title / Host and service notifications",
            id="custom title with macro",
        ),
    ],
)
def test_bar_chart_title(properties, settings, result):
    assert bar_chart_title(properties, {}, settings) == result
