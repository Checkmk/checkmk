#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest import MonkeyPatch

import cmk.base.automations.check_mk as automations
from cmk.automations.results import AnalyseHostResult, GetServicesLabelsResult
from cmk.base.app import make_app
from cmk.base.automations.automations import AutomationContext
from cmk.base.config import LoadingResult
from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import Edition, edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.utils import paths
from cmk.utils.labels import LabelSource
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from tests.testlib.unit.base_configuration_scenario import Scenario
from tests.unit.cmk.base.empty_config import EMPTY_CONFIG


def test_registered_automations(edition: Edition) -> None:
    needed_automations = [
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

    if edition is not Edition.COMMUNITY:
        needed_automations += [
            "bake-agents",
            "notify",
        ]

    assert sorted(needed_automations) == sorted(make_app(edition).automations._automations.keys())


def test_analyse_host(monkeypatch: MonkeyPatch) -> None:
    additional_labels: dict[str, str] = {}
    additional_label_sources: dict[str, LabelSource] = {}
    if edition(paths.omd_root) is Edition.ULTIMATEMT:
        additional_labels = {"cmk/customer": "provider"}
        additional_label_sources = {"cmk/customer": "discovered"}

    ts = Scenario()
    ts.add_host(HostName("test-host"))
    ts.set_option(
        "host_labels",
        {
            "test-host": {
                "explicit": "ding",
            },
        },
    )
    config_cache = ts.apply(monkeypatch)

    label_sources: dict[str, LabelSource] = {
        "cmk/site": "discovered",
        "explicit": "explicit",
    }
    assert automations.automation_analyse_host(
        AutomationContext(
            edition=(app := make_app(edition(paths.omd_root))).edition,
            make_bake_on_restart=app.make_bake_on_restart,
            create_core=app.create_core,
            make_fetcher_trigger=app.make_fetcher_trigger,
        ),
        ["test-host"],
        AgentBasedPlugins.empty(),
        LoadingResult(loaded_config=EMPTY_CONFIG, config_cache=config_cache),
    ) == AnalyseHostResult(
        label_sources=label_sources | additional_label_sources,
        labels={
            "cmk/site": "unit",
            "explicit": "ding",
        }
        | additional_labels,
    )


def test_service_labels(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("test-host"))
    ts.set_ruleset(
        "service_label_rules",
        list[RuleSpec[dict[str, str]]](
            [
                {
                    "condition": {"service_description": [{"$regex": "CPU load"}]},
                    "id": "01",
                    "value": {"label1": "val1"},
                },
                {
                    "condition": {"service_description": [{"$regex": "CPU load"}]},
                    "id": "02",
                    "value": {"label2": "val2"},
                },
                {
                    "condition": {"service_description": [{"$regex": "CPU temp"}]},
                    "id": "03",
                    "value": {"label1": "val1"},
                },
            ]
        ),
    )
    config_cache = ts.apply(monkeypatch)

    assert automations.automation_get_service_labels(
        AutomationContext(
            edition=(app := make_app(edition(paths.omd_root))).edition,
            make_bake_on_restart=app.make_bake_on_restart,
            create_core=app.create_core,
            make_fetcher_trigger=app.make_fetcher_trigger,
        ),
        ["test-host", "CPU load", "CPU temp"],
        AgentBasedPlugins.empty(),
        LoadingResult(loaded_config=EMPTY_CONFIG, config_cache=config_cache),
    ) == GetServicesLabelsResult(
        {
            "CPU load": {"label1": "val1", "label2": "val2"},
            "CPU temp": {"label1": "val1"},
        }
    )
