#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.dashboard import dashlet_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_dashlet_registry_plugins() -> None:
    expected_plugins = [
        "hoststats",
        "servicestats",
        "eventstats",
        "notify_failed_notifications",
        "url",
        "pnpgraph",
        "view",
        "embedded_view",
        "linked_view",
        "user_messages",
        "nodata",
        "snapin",
    ]

    assert sorted(dashlet_registry.keys()) == sorted(expected_plugins)
