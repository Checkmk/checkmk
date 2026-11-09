#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from cmk.checkengine.plugins import InventoryPluginName, SectionName
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Command as CLICommand
from cmk.plugins.checkmk.cli.inventory import (
    _inventory_request,
    _InventoryRequest,
    cli_command_inventorize_marked_hosts,
    cli_command_inventory,
)
from cmk.plugins.checkmk.cli.options import FileCacheRequest, PluginSelectionRequest


def _declared[R](command: CLICommand[R]) -> list[str]:
    recorded = CLIRecordedOptions()
    command.request(recorded)
    return [option.long for option in recorded.options]


def test_inventory_declares_its_options_in_help_order() -> None:
    assert _declared(cli_command_inventory) == [
        "cache",
        "no-cache",
        "no-tcp",
        "usewalk",
        "snmp-backend",
        "force",
        "detect-sections",
        "plugins",
        "detect-plugins",
        "fake-dns",
    ]


def test_inventorize_marked_hosts_declares_its_options_in_help_order() -> None:
    assert _declared(cli_command_inventorize_marked_hosts) == [
        "cache",
        "no-cache",
        "no-tcp",
        "usewalk",
        "snmp-backend",
        "fake-dns",
    ]


def test_the_inventory_request_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions(
        [
            ("--usewalk", ""),
            ("--force", ""),
            ("--detect-sections", "lnx_if"),
            ("--plugins", "lnx_if"),
        ],
        logging.getLogger(__name__),
    )

    assert _inventory_request(options) == _InventoryRequest(
        file_cache=FileCacheRequest(cache=False, no_cache=False, no_tcp=False),
        usewalk=True,
        snmp_backend=None,
        force=True,
        plugin_selection=PluginSelectionRequest(
            detect_sections=frozenset({SectionName("lnx_if")}),
            plugins=frozenset({InventoryPluginName("lnx_if")}),
            detect_plugins=None,
        ),
        fake_dns=None,
    )
