#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import io
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import override

import pytest
from pytest import MonkeyPatch

import cmk.base.automations.check_mk as automations
from cmk.automations.results import (
    AnalyseHostResult,
    AnalyzeHostRuleEffectivenessResult,
    AutomationResult,
    GetServicesLabelsResult,
)
from cmk.automations.types import AutomationID
from cmk.base.automations.automations import (
    Automation,
    AutomationError,
    Automations,
    AutomationState,
    BaseConfigState,
    DiscoveredAutomation,
    NoState,
)
from cmk.base.config import LoadingResult
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.labels import LabelSource
from cmk.ruleset_matcher.matcher import RuleSpec
from tests.testlib.unit.automations import make_common_state
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
        make_common_state(
            LoadingResult(
                loaded_config=EMPTY_CONFIG,
                hosts_config=loading_result.hosts_config,
                host_tags=loading_result.host_tags,
                config_cache=loading_result.config_cache,
            )
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


def test_rule_effectiveness_is_not_answered_from_an_earlier_call(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("test-host"))
    state = make_common_state(ts.apply(monkeypatch))
    # CPython hands the address of a freed list to the next one, so the rules of a
    # later call may have the id of an earlier call's. Make that deterministic by
    # handing over the very same list object, with different rules in it.
    rules: list[list[RuleSpec[bool]]] = [
        [{"id": "01", "value": True, "condition": {"host_name": ["test-host"]}}]
    ]
    monkeypatch.setattr(ast, "literal_eval", lambda _text: rules)
    monkeypatch.setattr(sys, "stdin", io.StringIO())
    handler = automations.automation_analyze_host_rule_effectiveness.handler

    first = handler(state, [])
    rules[0][0]["condition"] = {"host_name": ["other-host"]}
    second = handler(state, [])

    assert (first, second) == (
        AnalyzeHostRuleEffectivenessResult({"01": True}),
        AnalyzeHostRuleEffectivenessResult({"01": False}),
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
        make_common_state(
            LoadingResult(
                loaded_config=EMPTY_CONFIG,
                hosts_config=loading_result.hosts_config,
                host_tags=loading_result.host_tags,
                config_cache=loading_result.config_cache,
            )
        ),
        ["test-host", "CPU load", "CPU temp"],
    ) == GetServicesLabelsResult(
        {
            "CPU load": {"label1": "val1", "label2": "val2"},
            "CPU temp": {"label1": "val1"},
        }
    )


class _Result(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("dummy")

    @override
    def serialize(self, for_cmk_version: str) -> str:
        return "dummy"


@dataclass
class _RecordingState(AutomationState):
    built_for: Path
    updated_for: list[Path] = field(default_factory=list)

    @override
    def update(self, omd_root: Path, _raw_config: Mapping[str, object]) -> None:
        self.updated_for.append(omd_root)


@dataclass(eq=False)  # hashed by identity: the engine keys states by factory
class _RecordingFactory:
    built: list[_RecordingState] = field(default_factory=list)

    def __call__(self, omd_root: Path, _raw_config: Mapping[str, object]) -> _RecordingState:
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


def _loaded_engine(plugins: Iterable[DiscoveredAutomation]) -> Automations:
    engine = Automations(plugins)
    engine.update(Path("/old"), {})
    return engine


@pytest.mark.usefixtures("disable_debug")
def test_execution_before_the_first_update_fails() -> None:
    engine = Automations([_automation("a", _RecordingFactory())])

    assert engine.execute(AutomationID("a"), []) is AutomationError.KNOWN_ERROR


def test_an_automation_without_state_needs_no_configuration() -> None:
    def handle(_state: NoState, _args: list[str]) -> _Result:
        return _Result()

    engine = Automations(
        [Automation(name=AutomationID("a"), state_factory=NoState, handler=handle, result=_Result)]
    )
    # Nothing can be derived from an empty mapping: a state that tried would fail.
    engine.update(Path("/old"), {})

    assert isinstance(engine.execute(AutomationID("a"), []), _Result)


def test_base_config_state_picks_the_base_configuration() -> None:
    raw_config = {f.name: getattr(EMPTY_CONFIG, f.name) for f in fields(EMPTY_CONFIG)} | {
        "FOLDER_PATH": None,  # read by load_raw_config(), but no base configuration
    }

    assert BaseConfigState(Path("/old"), raw_config).loaded_config == EMPTY_CONFIG


def test_only_automations_that_ask_for_it_read_the_configuration_under_lock() -> None:
    engine = Automations(
        [
            Automation(
                name=AutomationID("locked"),
                state_factory=_RecordingFactory(),
                handler=_handle,
                result=_Result,
                lock_configuration=True,
            ),
            _automation("unlocked", _RecordingFactory()),
        ]
    )

    assert [
        engine.wants_configuration_lock(AutomationID(name))
        for name in ("locked", "unlocked", "unknown")
    ] == [True, False, False]


def test_state_is_built_once_on_first_execution() -> None:
    factory = _RecordingFactory()
    engine = _loaded_engine([_automation("a", factory)])

    engine.execute(AutomationID("a"), [])
    engine.execute(AutomationID("a"), [])

    assert len(factory.built) == 1


def test_automations_naming_the_same_factory_share_one_state() -> None:
    factory = _RecordingFactory()
    engine = _loaded_engine([_automation("a", factory), _automation("b", factory)])

    engine.execute(AutomationID("a"), [])
    engine.execute(AutomationID("b"), [])

    assert len(factory.built) == 1


def test_update_reaches_the_built_states() -> None:
    factory = _RecordingFactory()
    engine = _loaded_engine([_automation("a", factory)])
    engine.execute(AutomationID("a"), [])

    engine.update(Path("/new"), {})

    assert factory.built[0].updated_for == [Path("/new")]


def test_update_leaves_unbuilt_states_alone() -> None:
    factory = _RecordingFactory()
    engine = _loaded_engine([_automation("a", factory)])

    engine.update(Path("/new"), {})

    assert not factory.built


def test_state_built_after_update_uses_the_new_arguments() -> None:
    factory = _RecordingFactory()
    engine = _loaded_engine([_automation("a", factory)])

    engine.update(Path("/new"), {})
    engine.execute(AutomationID("a"), [])

    assert [state.built_for for state in factory.built] == [Path("/new")]


def test_handler_output_does_not_reach_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    def chatty_handler(_state: _RecordingState, _args: list[str]) -> _Result:
        sys.stdout.write("chatter")
        return _Result()

    engine = _loaded_engine(
        [
            Automation(
                name=AutomationID("chatty"),
                state_factory=_RecordingFactory(),
                handler=chatty_handler,
                result=_Result,
            )
        ]
    )

    engine.execute(AutomationID("chatty"), [])

    assert capsys.readouterr().out == ""


@pytest.mark.usefixtures("disable_debug")
def test_output_of_a_failing_handler_reaches_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    def failing_handler(_state: _RecordingState, _args: list[str]) -> _Result:
        sys.stdout.write("chatter")
        raise MKGeneralException("broken")

    engine = _loaded_engine(
        [
            Automation(
                name=AutomationID("failing"),
                state_factory=_RecordingFactory(),
                handler=failing_handler,
                result=_Result,
            )
        ]
    )

    assert engine.execute(AutomationID("failing"), []) is AutomationError.KNOWN_ERROR
    assert capsys.readouterr().out == "chatter"
