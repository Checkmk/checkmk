#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import HostLabel, Metric, Result, State, StringTable, TableRow
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_switch_port_statuses import (
    check_switch_ports_statuses,
    CheckParams,
    discover_switch_ports_statuses,
    DiscoveryParams,
    host_label_meraki_switch_ports_statuses,
    inventorize_meraki_cdp_cache,
    inventorize_meraki_interfaces,
    inventorize_meraki_lldp_cache,
    parse_switch_ports_statuses,
    Section,
)
from cmk.plugins.cisco_meraki.lib.schema import RawSwitchPortStatus


class _RawSwitchPortStatusFactory(TypedDictFactory[RawSwitchPortStatus]):
    __check_model__ = False


def test_parsing_multiple_switch_ports() -> None:
    switch_port_status = [
        _RawSwitchPortStatusFactory.build(),
        _RawSwitchPortStatusFactory.build(),
        _RawSwitchPortStatusFactory.build(),
    ]
    string_table = [[f"{json.dumps(switch_port_status)}"]]
    section = parse_switch_ports_statuses(string_table)
    assert len(section) == 3


class TestDiscovery:
    @pytest.fixture
    def params(self) -> DiscoveryParams:
        return DiscoveryParams(
            admin_port_states=["up", "down"],
            operational_port_states=["up", "down"],
        )

    @pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
    def test_discover_switch_ports_statuses_no_payload(
        self, string_table: StringTable, params: DiscoveryParams
    ) -> None:
        section = parse_switch_ports_statuses(string_table)
        assert not any(discover_switch_ports_statuses(params, section))

    def test_discover_switch_ports_statuses_up(self, params: DiscoveryParams) -> None:
        switch_port_status = _RawSwitchPortStatusFactory.build(
            enabled=True,
            status="connected",
            speed="10 Gbps",
        )
        string_table = [[f"[{json.dumps(switch_port_status)}]"]]
        section = parse_switch_ports_statuses(string_table)
        service, *_ = discover_switch_ports_statuses(params, section)

        assert service.parameters == {
            "admin_state": "up",
            "operational_state": "up",
            "speed": "10 Gbps",
        }

    def test_discover_switch_ports_statuses_down(self, params: DiscoveryParams) -> None:
        switch_port_status = _RawSwitchPortStatusFactory.build(
            enabled=False,
            status="disconnected",
            speed="0 Gbps",
        )
        string_table = [[f"[{json.dumps(switch_port_status)}]"]]
        section = parse_switch_ports_statuses(string_table)
        service, *_ = discover_switch_ports_statuses(params, section)

        assert service.parameters == {
            "admin_state": "down",
            "operational_state": "down",
            "speed": "0 Gbps",
        }


class TestHostLabels:
    def _build_section(self, *, with_lldp: bool) -> Section:
        switch_port_status = _RawSwitchPortStatusFactory.build(**{} if with_lldp else {"lldp": {}})
        string_table = [[f"[{json.dumps(switch_port_status)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_without_lldp(self) -> None:
        section = self._build_section(with_lldp=False)
        assert not list(host_label_meraki_switch_ports_statuses(section))

    def test_with_lldp(self) -> None:
        section = self._build_section(with_lldp=True)

        value = list(host_label_meraki_switch_ports_statuses(section))
        expected = [HostLabel("cmk/meraki/has_lldp_neighbors", "yes")]

        assert value == expected


@pytest.fixture
def params() -> CheckParams:
    return CheckParams(
        show_traffic=True,
        state_admin_change=1,
        state_disabled=0,
        state_not_connected=0,
        state_not_full_duplex=1,
        state_op_change=1,
        state_speed_change=1,
    )


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_switch_ports_statuses_no_payload(
    string_table: StringTable, params: CheckParams
) -> None:
    section = parse_switch_ports_statuses(string_table)
    assert not list(check_switch_ports_statuses("", params, section))


class TestAdminStatus:
    @pytest.fixture
    def params(self, params: CheckParams) -> CheckParams:
        params["admin_state"] = "down"
        return params

    def _build_section(self, *, enabled: bool) -> Section:
        switch_port_status = _RawSwitchPortStatusFactory.build(portId="1", enabled=enabled)
        string_table = [[f"[{json.dumps(switch_port_status)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_disabled(self, params: CheckParams) -> None:
        section = self._build_section(enabled=False)

        value = list(check_switch_ports_statuses("1", params, section))
        expected = [
            Result(state=State.OK, summary="(admin down)", details="Admin status: down"),
        ]

        assert value == expected

    def test_enabled_with_status_change(self, params: CheckParams) -> None:
        section = self._build_section(enabled=True)

        value = list(check_switch_ports_statuses("1", params, section))[:2]
        expected = [
            Result(state=State.OK, notice="Admin status: up"),
            Result(state=State.WARN, summary="changed admin down -> up"),
        ]

        assert value == expected


class TestCheckOperationalStatus:
    @pytest.fixture
    def params(self, params: CheckParams) -> CheckParams:
        params["operational_state"] = "down"
        return params

    def _build_section(self, *, status: str) -> Section:
        switch_port_status = _RawSwitchPortStatusFactory.build(
            portId="1",
            enabled=True,
            status=status,
        )
        string_table = [[f"[{json.dumps(switch_port_status)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_disconnected(self, params: CheckParams) -> None:
        section = self._build_section(status="disconnected")

        value = list(check_switch_ports_statuses("1", params, section))[2:]
        expected = [
            Result(state=State.OK, summary="(down)", details="Operational status: down"),
        ]

        assert value == expected

    def test_connected_with_status_change(self, params: CheckParams) -> None:
        section = self._build_section(status="connected")

        value = list(check_switch_ports_statuses("1", params, section))[2:4]
        expected = [
            Result(state=State.OK, summary="(up)", details="Operational status: up"),
            Result(state=State.WARN, summary="changed down -> up"),
        ]

        assert value == expected


class TestCheckSpeed:
    @pytest.fixture
    def params(self, params: CheckParams) -> CheckParams:
        params["speed"] = "10 Gbps"
        return params

    def _build_section(self, *, speed: str) -> Section:
        switch_port_status = _RawSwitchPortStatusFactory.build(
            portId="1",
            enabled=True,
            status="connected",
            speed=speed,
        )
        string_table = [[f"[{json.dumps(switch_port_status)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_no_speed_change(self, params: CheckParams) -> None:
        section = self._build_section(speed="10 Gbps")

        value = list(check_switch_ports_statuses("1", params, section))[4]
        expected = Result(state=State.OK, summary="Speed: 10 Gbps")

        assert value == expected

    def test_with_speed_change(self, params: CheckParams) -> None:
        section = self._build_section(speed="20 Gbps")

        value = list(check_switch_ports_statuses("1", params, section))[4:6]
        expected = [
            Result(state=State.OK, summary="Speed: 20 Gbps"),
            Result(state=State.WARN, summary="changed 10 Gbps -> 20 Gbps"),
        ]

        assert value == expected


class TestCheckOtherResults:
    @pytest.fixture
    def params(self, params: CheckParams) -> CheckParams:
        params["admin_state"] = "up"
        params["operational_state"] = "up"
        params["speed"] = "10 Gbps"
        return params

    def _build_section(self, data: dict[str, object]) -> Section:
        defaults = {"portId": "1", "enabled": True, "status": "connected", "speed": "10 Gbps"}
        payload = {**defaults, **data}
        status_ = _RawSwitchPortStatusFactory.build(**payload)
        string_table = [[f"[{json.dumps(status_)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_traffic_bandwith(self, params: CheckParams) -> None:
        section = self._build_section({"trafficInKbps": {"total": 100.0, "sent": 60.0, "recv": 40}})

        value = list(check_switch_ports_statuses("1", params, section))[3:7]
        expected = [
            Result(state=State.OK, summary="In: 40.0 Bit/s"),
            Metric("if_in_bps", 40.0),
            Result(state=State.OK, summary="Out: 60.0 Bit/s"),
            Metric("if_out_bps", 60.0),
        ]

        assert value == expected

    def test_duplex(self, params: CheckParams) -> None:
        section = self._build_section({"duplex": "full"})

        value = list(check_switch_ports_statuses("1", params, section))[7]
        expected = Result(state=State.OK, notice="Duplex: full")

        assert value == expected

    def test_client_count(self, params: CheckParams) -> None:
        section = self._build_section({"clientCount": 42})

        value = list(check_switch_ports_statuses("1", params, section))[8]
        expected = Result(state=State.OK, notice="Clients: 42")

        assert value == expected

    def test_uplink_yes(self, params: CheckParams) -> None:
        section = self._build_section({"isUplink": True})

        value = list(check_switch_ports_statuses("1", params, section))[9]
        expected = Result(state=State.OK, summary="Uplink", details="Uplink: yes")

        assert value == expected

    def test_uplink_no(self, params: CheckParams) -> None:
        section = self._build_section({"isUplink": False})

        value = list(check_switch_ports_statuses("1", params, section))[9]
        expected = Result(state=State.OK, notice="Uplink: no")

        assert value == expected

    def test_power_usage(self, params: CheckParams) -> None:
        section = self._build_section({"powerUsageInWh": 200})

        value = list(check_switch_ports_statuses("1", params, section))[10]
        expected = Result(state=State.OK, summary="Power usage: 200.0 Wh")

        assert value == expected

    def test_spanning_tree_status(self, params: CheckParams) -> None:
        section = self._build_section({"spanningTree": {"statuses": ["Learning", "Cooling"]}})

        value = list(check_switch_ports_statuses("1", params, section))[11:13]
        expected = [
            Result(state=State.OK, notice="Spanning tree status: Learning"),
            Result(state=State.OK, notice="Spanning tree status: Cooling"),
        ]

        assert value == expected

    def test_warnings(self, params: CheckParams) -> None:
        section = self._build_section({"warnings": ["network unhealthy"]})

        value = list(check_switch_ports_statuses("1", params, section))[12]
        expected = Result(state=State.WARN, summary="network unhealthy")

        assert value == expected

    def test_errors(self, params: CheckParams) -> None:
        section = self._build_section({"errors": ["network down"]})

        value = list(check_switch_ports_statuses("1", params, section))[13]
        expected = Result(state=State.CRIT, summary="network down")

        assert value == expected

    def test_secure_port(self, params: CheckParams) -> None:
        # TODO: figure out why this should be an unknown status.
        section = self._build_section({"securePort": {"enabled": True}})

        value = list(check_switch_ports_statuses("1", params, section))[14]
        expected = Result(state=State.UNKNOWN, summary="Secure port: enabled")

        assert value == expected


class TestInventoryMerakiInterfaces:
    def _build_section(self, data: dict[str, object]) -> Section:
        defaults = {"portId": "1", "enabled": True, "speed": "10 Gbps"}
        payload = {**defaults, **data}
        status_ = _RawSwitchPortStatusFactory.build(**payload)
        string_table = [[f"[{json.dumps(status_)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_with_operational_status(self) -> None:
        section = self._build_section({"status": "connected"})

        value, *_ = inventorize_meraki_interfaces(section)
        expected = TableRow(
            path=["networking", "interfaces"],
            key_columns={"index": 1},
            inventory_columns={
                "name": "Port 1",
                "admin_status": 1,
                "oper_status": 1,
                "speed": "10 Gbps",
                "port_type": 6,
            },
            status_columns={},
        )

        assert value == expected

    def test_missing_optional_values(self) -> None:
        section = self._build_section({"status": "unknown"})

        value, *_ = inventorize_meraki_interfaces(section)
        expected = TableRow(
            path=["networking", "interfaces"],
            key_columns={"index": 1},
            inventory_columns={
                "name": "Port 1",
                "admin_status": 1,
                "speed": "10 Gbps",
                "port_type": 6,
            },
            status_columns={},
        )

        assert value == expected


class TestInventoryCDPCache:
    def _build_section(self, data: dict[str, object]) -> Section:
        defaults = {"portId": "1", "cdp": data}
        payload = {**defaults, **data}
        status_ = _RawSwitchPortStatusFactory.build(**payload)
        string_table = [[f"[{json.dumps(status_)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_without_data(self) -> None:
        section = self._build_section({})
        assert not list(inventorize_meraki_cdp_cache(section))

    def test_missing_optional_values(self) -> None:
        section = self._build_section(
            {
                "cdp": {
                    "portId": "Port 20",
                    "address": None,
                    "capabilities": None,
                    "deviceId": None,
                    "nativeVlan": None,
                    "platform": None,
                    "version": None,
                }
            }
        )

        value, *_ = inventorize_meraki_cdp_cache(section)
        expected = TableRow(
            path=["networking", "cdp_cache", "neighbors"],
            key_columns={"local_port": 1, "neighbor_name": "", "neighbor_port": "Port 20"},
            inventory_columns={},
            status_columns={},
        )

        assert value == expected

    def test_with_data(self) -> None:
        section = self._build_section(
            {
                "cdp": {
                    "portId": "Port 20",
                    "address": "10.0,0.1",
                    "capabilities": "Switch",
                    "deviceId": "0c8ddbddee:ff",
                    "nativeVlan": 1,
                    "platform": "MS350-24X",
                    "version": "1",
                }
            }
        )

        value, *_ = inventorize_meraki_cdp_cache(section)
        expected = TableRow(
            path=["networking", "cdp_cache", "neighbors"],
            key_columns={"local_port": 1, "neighbor_name": "", "neighbor_port": "Port 20"},
            inventory_columns={
                "capabilities": "Switch",
                "native_vlan": 1,
                "neighbor_address": "10.0,0.1",
                "neighbor_id": "0c8ddbddee:ff",
                "platform": "MS350-24X",
                "version": "1",
            },
            status_columns={},
        )

        assert value == expected


class TestInventoryLLDPCache:
    def _build_section(self, data: dict[str, object]) -> Section:
        defaults = {"portId": "1", "lldp": data}
        payload = {**defaults, **data}
        status_ = _RawSwitchPortStatusFactory.build(**payload)
        string_table = [[f"[{json.dumps(status_)}]"]]
        return parse_switch_ports_statuses(string_table)

    def test_without_data(self) -> None:
        section = self._build_section({})
        assert not list(inventorize_meraki_lldp_cache(section))

    def test_missing_optional_values(self) -> None:
        section = self._build_section(
            {
                "lldp": {
                    "portId": "2",
                    "systemName": "MS350-24X - Test",
                    "chassisId": None,
                    "managementAddress": None,
                    "portDescription": None,
                    "systemCapabilities": None,
                    "systemDescription": None,
                }
            }
        )

        value, *_ = inventorize_meraki_lldp_cache(section)
        expected = TableRow(
            path=["networking", "lldp_cache", "neighbors"],
            key_columns={
                "local_port": 1,
                "neighbor_name": "MS350-24X - Test",
                "neighbor_port": "2",
            },
            inventory_columns={},
            status_columns={},
        )

        assert value == expected

    def test_with_data(self) -> None:
        section = self._build_section(
            {
                "lldp": {
                    "portId": "2",
                    "systemName": "MS350-24X - Test",
                    "chassisId": "0c:8d:db:dd:ee:ff",
                    "managementAddress": "10.0.0.100",
                    "portDescription": "Port 2",
                    "systemCapabilities": "switch",
                    "systemDescription": "MS350-24X Cloud Managed PoE Switch",
                }
            }
        )

        value, *_ = inventorize_meraki_lldp_cache(section)
        expected = TableRow(
            path=["networking", "lldp_cache", "neighbors"],
            key_columns={
                "local_port": 1,
                "neighbor_name": "MS350-24X - Test",
                "neighbor_port": "2",
            },
            inventory_columns={
                "capabilities": "switch",
                "neighbor_address": "10.0.0.100",
                "neighbor_id": "0c:8d:db:dd:ee:ff",
                "port_description": "Port 2",
                "system_description": "MS350-24X Cloud Managed PoE Switch",
            },
            status_columns={},
        )

        assert value == expected
