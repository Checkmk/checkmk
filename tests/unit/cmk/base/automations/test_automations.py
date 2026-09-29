#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import override

import pytest
from pytest import MonkeyPatch

import cmk.base.automations.check_mk as automations
import cmk.utils.paths
from cmk.automations.results import (
    ABCAutomationResult,
    AnalyseHostResult,
    GetServicesLabelsResult,
    SerializedResult,
)
from cmk.automations.types import AutomationID
from cmk.base.automations.automations import Automation, AutomationError, Automations, CommonState
from cmk.base.config import LoadingResult
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import Version
from cmk.ruleset_matcher.labels import LabelSource
from cmk.ruleset_matcher.matcher import RuleSpec
from tests.testlib.unit.base_configuration_scenario import Scenario
from tests.testlib.unit.empty_config import EMPTY_CONFIG


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
    loading_result = ts.apply(monkeypatch)

    label_sources: dict[str, LabelSource] = {
        "cmk/site": "discovered",
        "explicit": "explicit",
    }
    assert automations.automation_analyse_host.handler(
        CommonState(
            cmk.utils.paths.omd_root,
            LoadingResult(
                loaded_config=EMPTY_CONFIG,
                hosts_config=loading_result.hosts_config,
                host_tags=loading_result.host_tags,
                config_cache=loading_result.config_cache,
            ),
        ),
        ["test-host"],
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
    loading_result = ts.apply(monkeypatch)

    assert automations.automation_get_services_labels.handler(
        CommonState(
            cmk.utils.paths.omd_root,
            LoadingResult(
                loaded_config=EMPTY_CONFIG,
                hosts_config=loading_result.hosts_config,
                host_tags=loading_result.host_tags,
                config_cache=loading_result.config_cache,
            ),
        ),
        ["test-host", "CPU load", "CPU temp"],
    ) == GetServicesLabelsResult(
        {
            "CPU load": {"label1": "val1", "label2": "val2"},
            "CPU temp": {"label1": "val1"},
        }
    )


class _Result(ABCAutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("dummy")

    @override
    def serialize(self, for_cmk_version: Version) -> SerializedResult:
        return SerializedResult("dummy")


@dataclass
class _RecordingState:
    built_for: Path
    updated_for: list[Path] = field(default_factory=list)

    def update(self, omd_root: Path, _loading_result: LoadingResult | None) -> None:
        self.updated_for.append(omd_root)


@dataclass(eq=False)  # hashed by identity: the engine keys states by factory
class _RecordingFactory:
    built: list[_RecordingState] = field(default_factory=list)

    def __call__(self, omd_root: Path, _loading_result: LoadingResult | None) -> _RecordingState:
        self.built.append(state := _RecordingState(built_for=omd_root))
        return state


def _handle(_state: _RecordingState, _args: list[str]) -> _Result:
    return _Result()


def _automation(
    name: str, state_factory: _RecordingFactory
) -> Automation[_RecordingState, _Result]:
    return Automation(
        name=AutomationID(name),
        state_factory=state_factory,
        handler=_handle,
        result=_Result,
    )


def test_state_is_built_once_on_first_execution() -> None:
    factory = _RecordingFactory()
    engine = Automations([_automation("a", factory)], omd_root=Path("/old"), loading_result=None)

    engine.execute(AutomationID("a"), [])
    engine.execute(AutomationID("a"), [])

    assert len(factory.built) == 1


def test_automations_naming_the_same_factory_share_one_state() -> None:
    factory = _RecordingFactory()
    engine = Automations(
        [_automation("a", factory), _automation("b", factory)],
        omd_root=Path("/old"),
        loading_result=None,
    )

    engine.execute(AutomationID("a"), [])
    engine.execute(AutomationID("b"), [])

    assert len(factory.built) == 1


def test_update_reaches_the_built_states() -> None:
    factory = _RecordingFactory()
    engine = Automations([_automation("a", factory)], omd_root=Path("/old"), loading_result=None)
    engine.execute(AutomationID("a"), [])

    engine.update(Path("/new"), None)

    assert factory.built[0].updated_for == [Path("/new")]


def test_update_leaves_unbuilt_states_alone() -> None:
    factory = _RecordingFactory()
    engine = Automations([_automation("a", factory)], omd_root=Path("/old"), loading_result=None)

    engine.update(Path("/new"), None)

    assert not factory.built


def test_state_built_after_update_uses_the_new_arguments() -> None:
    factory = _RecordingFactory()
    engine = Automations([_automation("a", factory)], omd_root=Path("/old"), loading_result=None)

    engine.update(Path("/new"), None)
    engine.execute(AutomationID("a"), [])

    assert [state.built_for for state in factory.built] == [Path("/new")]


def test_handler_output_does_not_reach_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    def chatty_handler(_state: _RecordingState, _args: list[str]) -> _Result:
        sys.stdout.write("chatter")
        return _Result()

    engine = Automations(
        [
            Automation(
                name=AutomationID("chatty"),
                state_factory=_RecordingFactory(),
                handler=chatty_handler,
                result=_Result,
            )
        ],
        omd_root=Path("/old"),
        loading_result=None,
    )

    engine.execute(AutomationID("chatty"), [])

    assert capsys.readouterr().out == ""


@pytest.mark.usefixtures("disable_debug")
def test_output_of_a_failing_handler_reaches_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    def failing_handler(_state: _RecordingState, _args: list[str]) -> _Result:
        sys.stdout.write("chatter")
        raise MKGeneralException("broken")

    engine = Automations(
        [
            Automation(
                name=AutomationID("failing"),
                state_factory=_RecordingFactory(),
                handler=failing_handler,
                result=_Result,
            )
        ],
        omd_root=Path("/old"),
        loading_result=None,
    )

    assert engine.execute(AutomationID("failing"), []) is AutomationError.KNOWN_ERROR
    assert capsys.readouterr().out == "chatter"
