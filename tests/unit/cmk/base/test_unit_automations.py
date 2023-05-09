#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from tests.testlib.base import Scenario

import cmk.utils.version as cmk_version

from cmk.automations.results import AnalyseHostResult, GetServicesLabelsResult

import cmk.base.automations
import cmk.base.automations.check_mk as automations


def test_registered_automations():
    needed_automations = [
        "active-check",
        "analyse-host",
        "get-services-labels",
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


def test_analyse_host(monkeypatch):
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


def test_service_labels(monkeypatch):
    automation = automations.AutomationGetServicesLabels()

    ts = Scenario()
    ts.add_host("test-host")
    ts.set_ruleset(
        "service_label_rules",
        [
            {
                "condition": {"service_description": [{"$regex": "CPU load"}]},
                "value": {"label1": "val1"},
            },
            {
                "condition": {"service_description": [{"$regex": "CPU load"}]},
                "value": {"label2": "val2"},
            },
            {
                "condition": {"service_description": [{"$regex": "CPU temp"}]},
                "value": {"label1": "val1"},
            },
        ],
    )
    ts.apply(monkeypatch)

    assert automation.execute(["test-host", "CPU load", "CPU temp"]) == GetServicesLabelsResult(
        {
            "CPU load": {"label1": "val1", "label2": "val2"},
            "CPU temp": {"label1": "val1"},
        }
    )
