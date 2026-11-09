#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.discovery import discover_commands as cli_discover_commands


def test_available_commands() -> None:
    assert {m.selector.long for m in cli_discover_commands()} == {
        "automation",
        "browse-man",
        "check",
        "check-discovery",
        "cleanup-piggyback",
        "create-diagnostics-dump",
        "discover",
        "dump",
        "dump-agent",
        "flush",
        "inventorize-marked-hosts",
        "inventory",
        "list-checks",
        "list-hosts",
        "list-tag",
        "localize",
        "man",
        "nagios-config",
        "notify",
        "package",
        "reload",
        "restart",
        "snmpget",
        "snmptranslate",
        "snmpwalk",
        "update",
        "update-dns-cache",
        "version",
    }


def test_no_two_commands_claim_the_same_option() -> None:
    # Commands() rejects a collision; nothing else sees one, because the names above
    # are a set and a duplicate would collapse into it.
    CLICommands(plugins=cli_discover_commands())
