#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

from cmk.checkengine.plugins import InventoryPluginName, SectionName
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.plugins.checkmk.cli.inventory import (
    _FORCE_FLAG,
    _inventory_request,
    InventoryRequest,
)
from cmk.plugins.checkmk.cli.options import (
    _DETECT_SECTIONS_VALUE,
    _USEWALK_FLAG,
    FetchRequest,
    FileCacheRequest,
    INVENTORY_PLUGINS_VALUE,
    PluginSelectionRequest,
)


def test_the_inventory_request_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _USEWALK_FLAG: [""],
        _FORCE_FLAG: [""],
        _DETECT_SECTIONS_VALUE: ["lnx_if"],
        INVENTORY_PLUGINS_VALUE: ["lnx_if"],
        CLIArguments(placeholder="HOST1 HOST2...", parse=str): ["myhost"],
    }

    assert _inventory_request(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == InventoryRequest(
        fetch=FetchRequest(
            file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=False),
            usewalk=True,
            snmp_backend=None,
            fake_dns=None,
        ),
        force=True,
        plugin_selection=PluginSelectionRequest(
            detect_sections=frozenset({SectionName("lnx_if")}),
            plugins=frozenset({InventoryPluginName("lnx_if")}),
            detect_plugins=None,
        ),
        hosts=("myhost",),
    )
