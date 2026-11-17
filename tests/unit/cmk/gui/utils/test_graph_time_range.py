#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.type_defs import GraphTimerange
from cmk.gui.utils.graph_time_range import default_graph_time_range

_LAST_1_H = GraphTimerange(title="Last 1 h", duration=3600)
_LAST_4_H = GraphTimerange(title="Last 4 h", duration=4 * 3600)
_LAST_25_H = GraphTimerange(title="Last 25 h", duration=25 * 3600)


def test_last_4_h_is_the_default_when_configured() -> None:
    assert default_graph_time_range([_LAST_1_H, _LAST_4_H, _LAST_25_H]) == _LAST_4_H


def test_the_first_time_range_is_the_default_without_a_configured_last_4_h() -> None:
    assert default_graph_time_range([_LAST_1_H, _LAST_25_H]) == _LAST_1_H
