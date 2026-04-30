#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.automations.automations import discover_automations


def test_available_automations() -> None:
    assert {a.name for a in discover_automations()} == {
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
    }
