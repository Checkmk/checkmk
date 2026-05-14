#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.discover_plugins import discover_all_plugins, PluginGroup
from cmk.inventory_ui.v1_unstable import entry_point_prefixes


def test_inventory_ui_plugins_are_loadable() -> None:
    # in particular this tests against duplicate names.
    loaded = discover_all_plugins(
        PluginGroup.INVENTORY_UI,
        entry_point_prefixes(),
        skip_wrong_types=False,
        raise_errors=True,
    )
    assert not loaded.errors
