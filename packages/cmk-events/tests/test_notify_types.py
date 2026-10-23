#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.events.notify_types import (
    CustomPluginName,
    is_known_plugin,
    is_non_state_change_event_type,
    PluginNameWithParameters,
)


@pytest.mark.parametrize(
    "event_type, expected",
    [
        pytest.param("f", True, id="flapping"),
        pytest.param("af", True, id="alert handler failed"),
        pytest.param("rc", False, id="state change"),
    ],
)
def test_non_state_change_event_types_are_recognized(event_type: str, expected: bool) -> None:
    assert is_non_state_change_event_type(event_type) is expected


@pytest.mark.parametrize(
    "notify_plugin, expected",
    [
        pytest.param(("mail", None), True, id="built-in plug-in"),
        pytest.param((CustomPluginName("my_script"), None), False, id="custom plug-in"),
    ],
)
def test_only_builtin_plugins_are_known(
    notify_plugin: PluginNameWithParameters, expected: bool
) -> None:
    assert is_known_plugin(notify_plugin) is expected
