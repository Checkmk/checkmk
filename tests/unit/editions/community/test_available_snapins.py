#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.sidebar import snapin_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_snapins() -> None:
    expected_snapins = [
        "a_welcome",
        "admin_mini",
        "biaggr_groups",
        "biaggr_groups_tree",
        "bookmarks",
        "dashboards",
        "hostgroups",
        "master_control",
        "mkeventd_performance",
        "nagvis_maps",
        "performance",
        "search",
        "servicegroups",
        "sitestatus",
        "speedometer",
        "tactical_overview",
        "tag_tree",
        "time",
        "views",
        "wato_foldertree",
    ]

    assert sorted(snapin_registry.keys()) == sorted(expected_snapins)
