#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, NamedTuple
from unittest import mock

import cmk.utils.paths
from cmk.agent_based.legacy import discover_legacy_checks, FileLoader, find_plugin_files
from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from tests.testlib.common.repo import repo_path


class MissingCheckInfoError(KeyError):
    pass


class Check:
    _LEGACY_CHECKS: dict[str, LegacyCheckDefinition] = {}

    @classmethod
    def _load_checks(cls) -> None:
        for legacy_check in discover_legacy_checks(
            find_plugin_files(repo_path() / "cmk/base/legacy_checks"),
            FileLoader(
                precomile_path=cmk.utils.paths.precompiled_checks_dir,
                makedirs=lambda path: Path(path).mkdir(mode=0o770, exist_ok=True, parents=True),
            ),
            raise_errors=True,
        ).sane_check_info:
            cls._LEGACY_CHECKS[legacy_check.name] = legacy_check

    def __init__(self, name: str) -> None:
        self.name = name
        if not self._LEGACY_CHECKS:
            self._load_checks()

        if (info := self._LEGACY_CHECKS.get(name)) is None:
            raise MissingCheckInfoError(self.name)

        self.info = info

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def default_parameters(self) -> Mapping[str, Any]:
        return self.info.check_default_parameters or {}

    def run_parse(self, info: list) -> object:
        if self.info.parse_function is None:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no parse function defined")
        return self.info.parse_function(info)

    def run_discovery(self, info: object) -> Any:
        if self.info.discovery_function is None:
            raise MissingCheckInfoError(
                "Check '%s' " % self.name + "has no discovery function defined"
            )
        return self.info.discovery_function(info)

    def run_check(self, item: object, params: object, info: object) -> Any:
        if self.info.check_function is None:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no check function defined")
        return self.info.check_function(item, params, info)


class _MockValueStore:
    def __init__(self, getter: Callable) -> None:
        self._getter = getter

    def get(self, key, default=None):
        return self._getter(key, default)

    def __setitem__(self, key, value):
        pass


class _MockVSManager(NamedTuple):
    active_service_interface: _MockValueStore


def mock_item_state(mock_state):
    """Mock the calls to item_state API.

    Usage:

    with mock_item_state(mock_state):
        # run your check test here
        mocked_time_diff, mocked_value = \
            cmk.base.item_state.get_item_state('whatever_key', default="IGNORED")

    There are three different types of arguments to pass to mock_item_state:

    1) Callable object:
        The callable object will replace `get_item_state`. It must accept two
        arguments (key/default), in same way a dictionary does.

    2) Dictionary:
        The dictionary will replace the item states.
        Basically `get_item_state` gets replaced by the dictionaries GET method.

    3) Anything else:
        All calls to the item_state API behave as if the last state had
        been `mock_state`

    See for example 'test_statgrab_cpu_check.py'.
    """
    target = "cmk.agent_based.v1.value_store._active_host_value_store"

    getter = (  #
        mock_state.get
        if isinstance(mock_state, dict)
        else (mock_state if callable(mock_state) else lambda key, default: mock_state)  #
    )

    return mock.patch(target, _MockVSManager(_MockValueStore(getter)))
