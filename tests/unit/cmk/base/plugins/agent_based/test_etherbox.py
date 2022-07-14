#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs.pluginname import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckFunction, DiscoveryFunction
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.fixture(name="discovery", scope="module")
def _discovery(fix_register: FixRegister) -> DiscoveryFunction:
    return fix_register.check_plugins[CheckPluginName("etherbox_temp")].discovery_function


@pytest.fixture(name="check_smoke", scope="module")
def _check_smoke(fix_register: FixRegister) -> CheckFunction:
    return fix_register.check_plugins[CheckPluginName("etherbox_smoke")].check_function


@pytest.fixture(name="check_switch", scope="module")
def _check_switch(fix_register: FixRegister) -> CheckFunction:
    return fix_register.check_plugins[CheckPluginName("etherbox_switch")].check_function


@pytest.fixture(name="check_humidity", scope="module")
def _check_humidity(fix_register: FixRegister) -> CheckFunction:
    return fix_register.check_plugins[CheckPluginName("etherbox_humidity")].check_function


@pytest.fixture(name="check_temp", scope="module")
def _check_temp(fix_register: FixRegister) -> CheckFunction:
    return fix_register.check_plugins[CheckPluginName("etherbox_temp")].check_function


def test_discovery(discovery: DiscoveryFunction) -> None:
    # ignore second entry
    section = [
        [],
        [["", "9"], ["", "4"]],  # index
        [["", "n"], ["", "4"]],  # name
        [["", "1"], ["", "1"]],  # type
        [["", "1"], ["", "0"]],  # value
    ]
    services = list(discovery(section))
    assert services == [Service(item="9.1")]


def test_sensor_type_not_found(check_smoke: CheckFunction) -> None:
    section = [
        [],
        [["", "9"]],  # index
        [["", "n"]],  # name
        [["", "8"]],  # type
        [["", "42"]],  # value
    ]
    results = list(check_smoke(item="9.6", section=section, params={}))
    assert set(results) == {
        Result(state=State.UNKNOWN, summary="Sensor type changed 9.6"),
    }


def test_sensor_not_found(check_smoke: CheckFunction) -> None:
    section = [
        [],
        [["", "4"]],  # index
        [["", "n"]],  # name
        [["", "6"]],  # type
        [["", "42"]],  # value
    ]
    results = list(check_smoke(item="9.6", section=section, params={}))
    assert set(results) == {
        Result(state=State.UNKNOWN, summary="Sensor not found"),
    }


def test_check_smoke(check_smoke: CheckFunction) -> None:
    section = [
        [],
        [["", "9"]],  # index
        [["", "n"]],  # name
        [["", "6"]],  # type
        [["", "42"]],  # value
    ]
    results = list(check_smoke(item="9.6", section=section, params={}))
    assert set(results) == {
        Result(state=State.CRIT, summary="[n] Status: smoke alarm"),
        Metric("smoke", 42.0),
    }


def test_check_switch(check_switch: CheckFunction) -> None:
    section = [
        [],
        [["", "9"]],  # index
        [["", "n"]],  # name
        [["", "3"]],  # type
        [["", "42"]],  # value
    ]
    results = list(check_switch(item="9.3", section=section, params={}))
    assert set(results) == {
        Result(state=State.OK, summary="[n] Switch contact closed"),
        Metric("switch_contact", 42.0),
    }


def test_check_humidity(check_humidity: CheckFunction) -> None:
    section = [
        [],
        [["", "9"]],  # index
        [["", "n"]],  # name
        [["", "4"]],  # type
        [["", "42"]],  # value
    ]
    results = list(check_humidity(item="9.4", section=section, params={}))
    assert set(results) == {
        Result(state=State.OK, summary="[n] 4.20%"),
        Metric("humidity", 4.2, boundaries=(0, 100.0)),
    }


def test_check_temp(check_temp: CheckFunction) -> None:
    section = [
        [["0"]],
        [["", "9"]],  # index
        [["", "n"]],  # name
        [["", "1"]],  # type
        [["", "42"]],  # value
    ]
    results = list(check_temp(item="9.1", section=section, params={}))
    assert set(results) == {
        Result(state=State.OK, summary="[n] 4.2 °C"),
        Metric("temp", 4.2),
    }
