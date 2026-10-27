#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pytest_mock import MockerFixture

from cmk.bakery import v1, v2


@dataclass
class APIBakeletTestSet:
    conf: object
    mock_function: Callable[[MockerFixture, Path], None] = field(
        default=lambda _mocker, _tmp_path: None
    )
    files: Sequence[
        v1.Plugin
        | v1.SystemBinary
        | v2.Plugin
        | v2.SystemBinary
        | v2.PluginConfig
        | v2.SystemConfig
    ] = field(default_factory=list)
    scriptlets: Sequence[v2.Scriptlet] = field(default_factory=list)
    windows_configs: Sequence[
        (
            v2.WindowsConfigEntry
            | v2.WindowsConfigItems
            | v2.WindowsGlobalConfigEntry
            | v2.WindowsSystemConfigEntry
        )
    ] = field(default_factory=list)


def _assert_same_artifacts(actual: Sequence[object], expected: Sequence[object]) -> None:
    assert sorted(actual, key=repr) == sorted(expected, key=repr)


def run_v2_bakelet_test[ConfigType](
    bakelet: v2.BakeryPlugin[ConfigType],
    test_set: APIBakeletTestSet,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Run a standard API bakelet test against files, scriptlets, and windows config functions."""
    test_set.mock_function(mocker, tmp_path)
    assert isinstance(test_set.conf, dict)
    params = bakelet.parameter_parser(test_set.conf)

    _assert_same_artifacts(list(bakelet.files_function(params)), test_set.files)
    _assert_same_artifacts(list(bakelet.scriptlets_function(params)), test_set.scriptlets)
    _assert_same_artifacts(list(bakelet.windows_config_function(params)), test_set.windows_configs)
