#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import check_levels_predictive
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.interfaces import bandwidth_levels, BandwidthUnit, PredictiveLevels
from cmk.plugins.netapp import models

FcPortsSection = Mapping[str, models.FcPortModel]
FcInterfacesCountersSection = Mapping[str, models.FcInterfaceTrafficCountersModel]

# <<<netapp_ontap_fc_ports:sep(0)>>>
# {
#     "connected_speed": 0,
#     "description": "Fibre Channel Target Adapter 11a (QLogic CNA 8324 (8362), rev. 2, CNA_10G)",
#     "enabled": true,
#     "name": "11a",
#     "node_name": "mcc_darz_a-01",
#     "physical_protocol": "ethernet",
#     "state": "link_not_connected",
#     "supported_protocols": ["fcp"],
#     "wwnn": "50:0a:09:80:80:a2:f2:00",
#     "wwpn": "50:0a:09:88:a0:a2:f2:00",
# }
# {
#     "connected_speed": 0,
#     "description": "Fibre Channel Target Adapter 11b (QLogic CNA 8324 (8362), rev. 2, CNA_10G)",
#     "enabled": true,
#     "name": "11b",
#     "node_name": "mcc_darz_a-01",
#     "physical_protocol": "ethernet",
#     "state": "link_not_connected",
#     "supported_protocols": ["fcp"],
#     "wwnn": "50:0a:09:80:80:a2:f2:00",
#     "wwpn": "50:0a:09:87:a0:a2:f2:00",
# }
# <<<netapp_ontap_fc_interfaces_counters:sep(0)>>>
# {
#     "counters": [
#         {"name": "read_ops", "value": 0},
#         {"name": "write_ops", "value": 0},
#         {"name": "total_ops", "value": 0},
#         {"name": "read_data", "value": 0},
#         {"name": "write_data", "value": 0},
#         {"name": "average_read_latency", "value": 0},
#         {"name": "average_write_latency", "value": 0},
#     ],
#     "name": "port.11a",
#     "port_wwpn": "50:0a:09:88:a0:72:f1:c6",
#     "svm_name": "none",
#     "table": "fcp_lif:port",
# }
# {
#     "counters": [
#         {"name": "read_ops", "value": 0},  # rate/number
#         {"name": "write_ops", "value": 0},  # rate/number
#         {"name": "total_ops", "value": 0},  # rate/number
#         {"name": "read_data", "value": 0},  # rate/bytes
#         {"name": "write_data", "value": 0},  # rate/bytes
#         {"name": "average_read_latency", "value": 0},  # ms
#         {"name": "average_write_latency", "value": 0},  # ms
#     ],
#     "name": "port.11a",
#     "port_wwpn": "50:0a:09:88:a0:a2:f2:00",
#     "svm_name": "none",
#     "table": "fcp_lif:port",
# }


def parse_netapp_ontap_fc_ports(
    string_table: StringTable,
) -> FcPortsSection:
    return {
        f"{fc_port.node_name}.{fc_port.name}": fc_port
        for vol in string_table
        for fc_port in [models.FcPortModel.model_validate_json(vol[0])]
    }


agent_section_netapp_ontap_fc_ports = AgentSection(
    name="netapp_ontap_fc_ports",
    parse_function=parse_netapp_ontap_fc_ports,
)


def parse_netapp_ontap_fc_interfaces_counters(
    string_table: StringTable,
) -> FcInterfacesCountersSection:
    return {
        counter_obj.port_wwpn: counter_obj
        for line in string_table
        for counter_obj in [models.FcInterfaceTrafficCountersModel.model_validate_json(line[0])]
    }


agent_section_netapp_ontap_fc_interfaces_counters = AgentSection(
    name="netapp_ontap_fc_interfaces_counters",
    parse_function=parse_netapp_ontap_fc_interfaces_counters,
)


def discovery_netapp_ontap_fcp(
    section_netapp_ontap_fc_ports: FcPortsSection | None,
    section_netapp_ontap_fc_interfaces_counters: FcInterfacesCountersSection | None,
) -> DiscoveryResult:
    if not section_netapp_ontap_fc_ports:
        return

    settings: dict[str, str | int] = {}
    for port_name, port in section_netapp_ontap_fc_ports.items():
        if port.state != "online":
            continue

        settings["inv_state"] = port.state
        if (speed_in_bps := port.speed_in_bps()) is not None:
            settings["inv_speed"] = speed_in_bps
        yield Service(item=port_name, parameters=settings)


def check_netapp_ontap_fcp(
    item: str,
    params: Mapping[str, Any],
    section_netapp_ontap_fc_ports: FcPortsSection | None,
    section_netapp_ontap_fc_interfaces_counters: FcInterfacesCountersSection | None,
) -> CheckResult:
    if not section_netapp_ontap_fc_ports or not section_netapp_ontap_fc_interfaces_counters:
        return

    if not (fcp_if := section_netapp_ontap_fc_ports.get(item)):
        return

    now = time.time()
    counters = {
        counter.port_wwpn: counter
        for counter in section_netapp_ontap_fc_interfaces_counters.values()
        if counter.port_wwpn
    }

    fcp_if_counters: dict[str, int | float] = {
        counter["name"].replace("data", "bytes").replace("average", "avg"): counter["value"]
        for counter in counters[fcp_if.wwpn].counters
    }
    fcp_if_counters["now"] = now

    yield from _io_bytes_results(item, params, fcp_if_counters, fcp_if.speed_in_bps())

    yield from _speed_result(params, fcp_if.speed_in_bps())

    yield from _io_ops_results(item, params, fcp_if_counters)
    yield from _latency_results(item, params, fcp_if_counters)

    yield Result(
        state=State.OK,
        summary=f"State: {fcp_if.state}",
        details=f"State: {fcp_if.state}\nAddress {fcp_if.wwpn}",
    )


def _speed_result(params: Mapping[str, Any], speed: int | None) -> CheckResult:
    speed_str = None if speed is None else render.nicspeed(float(speed) / 8.0)
    expected_speed = params.get("speed", params.get("inv_speed"))
    expected_speed_str = (
        None if expected_speed is None else render.nicspeed(float(expected_speed) / 8.0)
    )

    if speed is None:
        if expected_speed is not None:
            yield Result(
                state=State.WARN, summary=f"Speed: unknown (expected: {expected_speed_str})"
            )
        return

    if expected_speed is None or speed == expected_speed:
        yield Result(state=State.OK, summary=f"Speed: {speed_str}")
        return

    yield Result(state=State.CRIT, summary=f"Speed: {speed_str} (expected: {expected_speed_str})")


def _io_bytes_results(
    item: str, params: Mapping[str, Any], fcp_if: Mapping[str, int | float], speed: int | None
) -> CheckResult:
    bw_levels = bandwidth_levels(
        params=params,
        speed_in=speed,
        speed_out=None,
        speed_total=None,
        unit=BandwidthUnit.BYTE,
    )

    value_store = get_value_store()
    now = fcp_if["now"]
    for what, levels, descr in [
        ("read_bytes", bw_levels.input, "Read"),
        ("write_bytes", bw_levels.output, "Write"),
    ]:
        if (counter_val := fcp_if.get(what)) is None:
            continue

        value = get_rate(value_store, f"{item}.{what}", now, counter_val, raise_overflow=True)
        if value is None:
            continue

        if isinstance(levels, PredictiveLevels):
            yield from check_levels_predictive(
                value=value,
                metric_name=what,
                levels=levels.config,
                render_func=render.iobandwidth,
                label=descr,
            )
        else:
            yield from check_levels_v1(
                value=value,
                metric_name=what,
                levels_upper=levels.upper or None,
                levels_lower=levels.lower or None,
                render_func=render.iobandwidth,
                label=descr,
            )


def _io_ops_results(
    item: str, params: Mapping[str, Any], fcp_if: Mapping[str, int | float]
) -> CheckResult:
    now = fcp_if["now"]
    value_store = get_value_store()
    for what, descr in [
        ("read_ops", "Read OPS"),
        ("write_ops", "Write OPS"),
    ]:
        if (counter_val := fcp_if.get(what)) is None:
            continue

        value = get_rate(value_store, f"{item}.{what}", now, counter_val, raise_overflow=True)
        if value is None:
            continue

        yield from check_levels_v1(
            value=value, metric_name=what, render_func=str, label=descr, notice_only=True
        )


def _latency_results(
    item: str, params: Mapping[str, Any], fcp_if: Mapping[str, int | float]
) -> CheckResult:
    total_ops = fcp_if["total_ops"]
    value_store = get_value_store()
    for what, text in [
        ("avg_latency", "Latency"),
        ("avg_read_latency", "Read Latency"),
        ("avg_write_latency", "Write Latency"),
    ]:
        if (counter_val := fcp_if.get(what)) is None:
            continue

        counter_val /= 1000

        try:
            # According to NetApp's "Performance Management Design Guide",
            # the latency is a function of `total_ops`.
            value = get_rate(
                value_store, f"{item}.{what}", total_ops, counter_val, raise_overflow=True
            )
        except IgnoreResultsError:
            continue

        levels_upper = params.get(what)
        if isinstance(levels_upper, dict):
            yield from check_levels_predictive(
                value=value, metric_name=f"{what}_latency", levels=levels_upper, label=text
            )
        else:
            yield from check_levels_v1(
                value=value,
                metric_name=f"{what}_latency",
                levels_upper=levels_upper,
                label=text,
                notice_only=True,
            )


check_plugin_netapp_ontap_fcp = CheckPlugin(
    name="netapp_ontap_fcp",
    service_name="Interface FCP %s",
    sections=[
        "netapp_ontap_fc_ports",
        "netapp_ontap_fc_interfaces_counters",
    ],
    discovery_function=discovery_netapp_ontap_fcp,
    check_function=check_netapp_ontap_fcp,
    check_ruleset_name="fcp",
    check_default_parameters={},
)
