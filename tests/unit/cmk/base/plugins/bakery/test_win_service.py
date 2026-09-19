#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import ValidationError

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.win_service import get_win_service_windows_config


def test_win_service_all_keys() -> None:
    conf = {
        "restart_on_crash": "no",
        "error_mode": "ignore",
        "start_mode": "disabled",
    }
    result = list(get_win_service_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["system", "service", "restart_on_crash"], content="no"),
        WindowsConfigEntry(path=["system", "service", "error_mode"], content="ignore"),
        WindowsConfigEntry(path=["system", "service", "start_mode"], content="disabled"),
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
        list(get_win_service_windows_config(conf))


def test_win_service_rejects_unknown_choices() -> None:
    conf = {"restart_on_crash": "yes", "error_mode": "log", "start_mode": "stopped"}
    with pytest.raises(ValidationError):
        list(get_win_service_windows_config(conf))


def test_win_service_unknown_keys_ignored() -> None:
    conf = {"restart_on_crash": "yes", "error_mode": "log", "start_mode": "auto"}
    result = list(get_win_service_windows_config({**conf, "unknown_key": "value"}))
    assert result == list(get_win_service_windows_config(conf))
