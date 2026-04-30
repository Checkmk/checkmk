#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.modes.modes import discover_modes


def test_available_modes() -> None:
    assert {m.name for m in discover_modes()} == {
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
