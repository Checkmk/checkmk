#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from cmk.gui.dashboard.dashlet.dashlets.stats import HostStatsDashlet
from cmk.gui.dashboard.page_edit_dashlet import _keys_not_managed_by_editor
from cmk.gui.dashboard.type_defs import DashletConfig


def test_keys_not_managed_by_editor_takes_over_layout_keys_only() -> None:
    dashlet_spec = DashletConfig(
        {
            "type": "hoststats",
            "size": (40, 20),
            "position": (31, 1),
            "title": "My title",
            "show_title": True,
            "context": {"host": {"host": "heute"}},
            "single_infos": ["host"],
        }
    )

    assert _keys_not_managed_by_editor(dashlet_spec, HostStatsDashlet) == {
        "type": "hoststats",
        "size": (40, 20),
        "position": (31, 1),
    }


def test_keys_not_managed_by_editor_falls_back_to_initial_size() -> None:
    dashlet_spec = DashletConfig({"type": "hoststats", "position": (1, 1)})

    assert _keys_not_managed_by_editor(dashlet_spec, HostStatsDashlet) == {
        "type": "hoststats",
        "size": HostStatsDashlet.initial_size(),
        "position": (1, 1),
    }
