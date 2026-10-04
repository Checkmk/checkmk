#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import override

import pytest

from cmk.automations.internal import (
    Automation,
    AutomationID,
    AutomationResult,
    AutomationState,
    NoState,
)
from cmk.base.automations.automations import (
    AutomationError,
    Automations,
    BaseConfigState,
    DiscoveredAutomation,
)
from cmk.ccc.exceptions import MKGeneralException
from tests.testlib.unit.empty_config import EMPTY_CONFIG


class _Result(AutomationResult):
    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("dummy")

    @override
    def serialize(self, for_cmk_version: str) -> str:
        return "dummy"


def _result_named(name: str) -> type[_Result]:
    """A result type for the automation of the given name, as the engine demands."""

    class _NamedResult(_Result):
        @staticmethod
        @override
        def automation_call() -> AutomationID:
            return AutomationID(name)

    return _NamedResult


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
        result=_result_named(name),
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
        [
            Automation(
                name=AutomationID("a"),
                state_factory=NoState,
                handler=handle,
                result=_result_named("a"),
            )
        ]
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
                result=_result_named("locked"),
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
                result=_result_named("chatty"),
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
                result=_result_named("failing"),
            )
        ]
    )

    assert engine.execute(AutomationID("failing"), []) is AutomationError.KNOWN_ERROR
    assert capsys.readouterr().out == "chatter"
