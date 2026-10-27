#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import ValidationError

from cmk.bakery.v2 import WindowsConfigEntry
from cmk.plugins.windows.bakery.win_service import (
    bakery_plugin_win_service,
    get_win_service_windows_config,
)


@pytest.mark.parametrize(
    "restart_on_crash, error_mode, start_mode",
    [
        pytest.param("no", "ignore", "disabled", id="non_defaults"),
        pytest.param("yes", "log", "auto", id="agent_defaults"),
    ],
)
def test_win_service_all_keys(restart_on_crash: str, error_mode: str, start_mode: str) -> None:
    conf = {
        "restart_on_crash": restart_on_crash,
        "error_mode": error_mode,
        "start_mode": start_mode,
    }
    result = list(get_win_service_windows_config(bakery_plugin_win_service.parameter_parser(conf)))
    assert result == [
        WindowsConfigEntry(
            path=["system", "service", "restart_on_crash"], content=restart_on_crash
        ),
        WindowsConfigEntry(path=["system", "service", "error_mode"], content=error_mode),
        WindowsConfigEntry(path=["system", "service", "start_mode"], content=start_mode),
    ]


@pytest.mark.parametrize(
    "conf",
    [
        pytest.param({}, id="empty"),
        pytest.param({"restart_on_crash": "no"}, id="partial"),
    ],
)
def test_win_service_rejects_missing_keys(conf: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        list(get_win_service_windows_config(bakery_plugin_win_service.parameter_parser(conf)))


def test_win_service_rejects_unknown_choices() -> None:
    conf = {"restart_on_crash": "yes", "error_mode": "log", "start_mode": "stopped"}
    with pytest.raises(ValidationError):
        list(get_win_service_windows_config(bakery_plugin_win_service.parameter_parser(conf)))


def test_win_service_unknown_keys_ignored() -> None:
    conf = {"restart_on_crash": "yes", "error_mode": "log", "start_mode": "auto"}
    result = list(
        get_win_service_windows_config(
            bakery_plugin_win_service.parameter_parser({**conf, "unknown_key": "value"})
        )
    )
    assert result == list(
        get_win_service_windows_config(bakery_plugin_win_service.parameter_parser(conf))
    )
