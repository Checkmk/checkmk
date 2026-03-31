#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Final

from cmk.base.app import make_app
from cmk.base.automations.automations import Automations
from cmk.ccc.version import Edition

EDITION = Edition.COMMUNITY


def test_registered_modes() -> None:
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

    assert sorted(expected) == sorted([m.long_option for m in make_app(EDITION).modes._modes])


NEEDED_AUTOMATIONS: Final = [
    "active-check",
    "analyse-host",
    "analyze-host-rule-effectiveness",
    "analyze-host-rule-matches",
    "analyze-service-rule-matches",
    "get-services-labels",
    "analyse-service",
    "create-diagnostics-dump",
    "delete-hosts",
    "delete-hosts-known-remote",
    "diag-cmk-agent",
    "diag-host",
    "diag-snmp",
    "diag-special-agent",
    "autodiscovery",
    "service-discovery",
    "service-discovery-preview",
    "special-agent-discovery-preview",
    "get-agent-output",
    "get-check-information",
    "get-configuration",
    "get-section-information",
    "get-service-name",
    "notification-analyse",
    "notification-get-bulks",
    "notification-replay",
    "notification-test",
    "ping-host",
    "reload",
    "rename-hosts",
    "restart",
    "scan-parents",
    "set-autochecks-v2",
    "update-dns-cache",
    "update-host-labels",
    "update-passwords-merged-file",
    "find-unknown-check-parameter-rule-sets",
]


def test_registered_automations() -> None:
    assert sorted(NEEDED_AUTOMATIONS) == sorted(make_app(EDITION).automations._automations.keys())


def test_discovered_automations() -> None:
    a = Automations()
    a.discover()
    assert sorted(NEEDED_AUTOMATIONS) == sorted(a._automations.keys())
