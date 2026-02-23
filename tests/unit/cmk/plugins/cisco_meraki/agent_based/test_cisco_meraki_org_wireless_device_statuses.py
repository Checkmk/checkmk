#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_wireless_device_statuses import (
    check_wireless_device_statuses_bands,
    check_wireless_device_statuses_ssids,
    CheckParams,
    discover_wireless_device_statuses_bands,
    discover_wireless_device_statuses_ssids,
    parse_wireless_device_statuses,
)
from cmk.plugins.cisco_meraki.lib.schema import RawWirelessDeviceStatus


class _RawWirelessDeviceStatusFactory(TypedDictFactory[RawWirelessDeviceStatus]):
    __check_model__ = False


class TestWirelessDeviceStatusesSSIDs:
    @pytest.fixture
    def params(self) -> CheckParams:
        return CheckParams(state_if_not_enabled=State.WARN.value)

    def test_discover(self) -> None:
        status = _RawWirelessDeviceStatusFactory.build(
            basicServiceSets=[
                {"ssidNumber": "1", "ssidName": "SSID 1"},
                {"ssidNumber": "2", "ssidName": "SSID 2"},
            ]
        )
        string_table = [[f"[{json.dumps(status)}]"]]
        section = parse_wireless_device_statuses(string_table)
        assert section

        value = list(discover_wireless_device_statuses_ssids(section))
        expected = [
            Service(item="SSID 1"),
            Service(item="SSID 2"),
        ]

        assert value == expected

    def test_check(self, params: CheckParams) -> None:
        status = _RawWirelessDeviceStatusFactory.build(
            basicServiceSets=[
                {
                    "ssidNumber": "1",
                    "ssidName": "SSID 1",
                    "enabled": True,
                    "visible": True,
                },
            ]
        )
        string_table = [[f"[{json.dumps(status)}]"]]
        section = parse_wireless_device_statuses(string_table)
        assert section

        value = list(check_wireless_device_statuses_ssids("SSID 1", params, section))
        expected = [
            Result(state=State.OK, summary="Status: Enabled"),
            Result(state=State.OK, notice="Visible: True"),
            Result(state=State.OK, notice="SSID number: 1"),
        ]

        assert value == expected

    def test_check_ssid_disabled(self, params: CheckParams) -> None:
        status = _RawWirelessDeviceStatusFactory.build(
            basicServiceSets=[{"ssidName": "SSID 1", "enabled": False}]
        )
        string_table = [[f"[{json.dumps(status)}]"]]
        section = parse_wireless_device_statuses(string_table)
        assert section

        value = list(check_wireless_device_statuses_ssids("SSID 1", params, section))
        expected = [Result(state=State.WARN, summary="Status: Disabled")]

        assert value == expected


class TestWirelessDeviceStatusesBands:
    def test_discover(self) -> None:
        status = _RawWirelessDeviceStatusFactory.build(
            basicServiceSets=[
                {"band": "2.4 GHz"},
                {"band": "5 GHz"},
            ]
        )
        string_table = [[f"[{json.dumps(status)}]"]]
        section = parse_wireless_device_statuses(string_table)
        assert section

        value = list(discover_wireless_device_statuses_bands(section))
        expected = [
            Service(item="2.4 GHz"),
            Service(item="5 GHz"),
        ]

        assert value == expected

    def test_check(self) -> None:
        status = _RawWirelessDeviceStatusFactory.build(
            basicServiceSets=[
                {
                    "band": "2.4 GHz",
                    "channel": 11,
                    "channelWidth": "20 MHz",
                    "power": "18 dBM",
                    "broadcasting": True,
                },
            ]
        )
        string_table = [[f"[{json.dumps(status)}]"]]
        section = parse_wireless_device_statuses(string_table)
        assert section

        value = list(check_wireless_device_statuses_bands("2.4 GHz", section))
        expected = [
            Result(state=State.OK, summary="Channel: 11"),
            Result(state=State.OK, summary="Channel width: 20 MHz"),
            Result(state=State.OK, summary="Power: 18 dBM"),
            Result(state=State.OK, notice="Broadcasting: True"),
            Metric("channel", 11.0),
            Metric("channel_width", 20000000.0),
            Metric("signal_power", 18.0),
        ]

        assert value == expected

    def test_check_missing_values(self) -> None:
        status = _RawWirelessDeviceStatusFactory.build(
            basicServiceSets=[
                {
                    "band": "2.4 GHz",
                    "channel": 11,
                    "broadcasting": True,
                    "channelWidth": None,
                    "power": None,
                },
            ]
        )
        string_table = [[f"[{json.dumps(status)}]"]]
        section = parse_wireless_device_statuses(string_table)
        assert section

        value = list(check_wireless_device_statuses_bands("2.4 GHz", section))
        expected = [
            Result(state=State.OK, summary="Channel: 11"),
            Result(state=State.OK, summary="Channel width: None"),
            Result(state=State.OK, summary="Power: None"),
            Result(state=State.OK, notice="Broadcasting: True"),
            Metric("channel", 11.0),
        ]

        assert value == expected
