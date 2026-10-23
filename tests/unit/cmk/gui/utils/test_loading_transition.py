#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.loading_transition import loading_transition_onclick, LoadingTransition


def test_onclick_hands_the_click_event_to_the_transition() -> None:
    assert loading_transition_onclick(LoadingTransition.table) == (
        "cmk.utils.makeLoadingTransition('table', 1000, undefined, event);"
    )


def test_onclick_quotes_the_title_as_a_javascript_string() -> None:
    assert loading_transition_onclick(LoadingTransition.table, title="Host's parameters") == (
        """cmk.utils.makeLoadingTransition('table', 1000, "Host's parameters", event);"""
    )
