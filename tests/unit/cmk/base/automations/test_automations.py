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
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.utils.labels import LabelSource
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from tests.testlib.common.empty_config import EMPTY_CONFIG
from tests.testlib.unit.base_configuration_scenario import Scenario


def test_analyse_host(monkeypatch: MonkeyPatch) -> None:
    additional_labels: dict[str, str] = {}
    additional_label_sources: dict[str, LabelSource] = {}

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
            edition=(app := make_app(Edition.COMMUNITY)).edition,
            make_bake_on_restart=app.make_bake_on_restart,
            create_core=app.create_core,
            make_fetcher_trigger=app.make_fetcher_trigger,
            make_metric_backend_fetcher=app.make_metric_backend_fetcher,
            get_builtin_host_labels=app.get_builtin_host_labels,
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
            edition=(app := make_app(Edition.COMMUNITY)).edition,
            make_bake_on_restart=app.make_bake_on_restart,
            create_core=app.create_core,
            make_fetcher_trigger=app.make_fetcher_trigger,
            make_metric_backend_fetcher=app.make_metric_backend_fetcher,
            get_builtin_host_labels=app.get_builtin_host_labels,
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
