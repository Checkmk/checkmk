#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.app import make_app
from cmk.ccc.version import Edition


def test_registered_modes(edition: Edition) -> None:
    expected = [
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
        "help",
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
    ]

    if edition is not Edition.COMMUNITY:
        expected += [
            "bake-agents",
            "cap",
            "checker",
            "compress-history",
            "convert-rrds",
            "dump-cmc-config",
            "dump-cmc-state",
            "handle-alerts",
            "real-time-checks",
        ]

    assert sorted(expected) == sorted([m.long_option for m in make_app(edition).modes._modes])
