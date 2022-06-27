#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.base import Scenario

import cmk.utils.version as cmk_version

from cmk.automations.results import AnalyseHostResult

import cmk.base.automations
import cmk.base.automations.check_mk as automations


def test_registered_automations() -> None:
    needed_automations = [
        "active-check",
        "analyse-host",
        "analyse-service",
        "create-diagnostics-dump",
        "delete-hosts",
        "delete-hosts-known-remote",
        "diag-host",
        "get-agent-output",
        "get-check-information",
        "get-configuration",
        "get-section-information",
        "inventory",
        "notification-analyse",
        "notification-get-bulks",
        "notification-replay",
        "reload",
        "rename-hosts",
        "restart",
        "scan-parents",
        "set-autochecks",
        "try-inventory",
        "update-dns-cache",
        "update-host-labels",
    ]

    if not cmk_version.is_raw_edition():
        needed_automations += [
            "bake-agents",
        ]

    assert sorted(needed_automations) == sorted(
        cmk.base.automations.automations._automations.keys()
    )


def test_analyse_host(monkeypatch) -> None:
    automation = automations.AutomationAnalyseHost()

    ts = Scenario()
    ts.add_host("test-host")
    ts.set_option(
        "host_labels",
        {
            "test-host": {
                "explicit": "ding",
            },
        },
    )
    ts.apply(monkeypatch)

    assert automation.execute(["test-host"]) == AnalyseHostResult(
        label_sources={"cmk/site": "discovered", "explicit": "explicit"},
        labels={"cmk/site": "NO_SITE", "explicit": "ding"},
    )
