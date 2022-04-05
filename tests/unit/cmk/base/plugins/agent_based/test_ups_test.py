#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

check_name = "ups_test"

_DAYS = 3600 * 24

DEFAULT_PARAMS = {"levels_elapsed_time": None}
PARAMS = {"levels_elapsed_time": (2 * _DAYS, 3 * _DAYS)}


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda p, s: plugin.check_function(params=p, section=s)


def test_discover_nothing(discover_ups_test) -> None:
    assert not list(discover_ups_test([[["3600"]], []]))


def test_discover(discover_ups_test) -> None:
    assert list(discover_ups_test([[["3600"]], [["1", "15000000", ""]]])) == [Service()]


@pytest.mark.parametrize(
    "raw_state, state, summary",
    [
        ("1", State.OK, "Last test: passed (details)"),
        ("2", State.WARN, "Last test: warning (details)"),
        ("3", State.CRIT, "Last test: error (details)"),
        ("4", State.CRIT, "Last test: aborted (details)"),
        ("5", State.OK, "Last test: in progress (details)"),
        ("6", State.OK, "Last test: no tests initiated (details)"),
    ],
)
def test_check_ups_test_result_details(
    raw_state: str, state: State, summary: str, check_ups_test
) -> None:
    result, *_ = check_ups_test(DEFAULT_PARAMS, [[["3600"]], [[raw_state, "0", "details"]]])
    assert result == Result(state=state, summary=summary)


def test_check_ups_test_time_check_no_start_time(check_ups_test) -> None:
    _, result, *_ = check_ups_test(DEFAULT_PARAMS, [[["0"]], [["1", "10", ""]]])
    assert result.state is State.OK
    assert result.summary.startswith("No battery test since start of device")


def test_check_ups_test_time_check_start_time_warn(check_ups_test) -> None:
    _, result, *_ = check_ups_test(PARAMS, [[[str(360000 * 52)]], [["1", "1000", ""]]])
    assert result.state is State.WARN
    assert result.summary.startswith("Time since start of last test: 2.1 d")
