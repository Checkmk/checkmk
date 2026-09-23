#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.redfish.lib import (
    parse_redfish_multiple,
    redfish_health_state,
    RedfishAPIData,
)

agent_section_redfish_networkadapters = AgentSection(
    name="redfish_networkadapters",
    parse_function=parse_redfish_multiple,
    parsed_section_name="redfish_networkadapters",
)


def discovery_redfish_networkadapters(section: RedfishAPIData) -> DiscoveryResult:
    for key in section.keys():
        if section[key].get("Status", {}).get("State") in [
            "Absent",
            "Disabled",
            "Offline",
            "UnavailableOffline",
        ]:
            continue
        if "PhysicalPorts" in section[key]:
            yield Service(
                item=section[key]["Id"],
                parameters={
                    "discovered_ports": [
                        port_id
                        for port in _physical_ports(section[key])
                        if port.get("LinkStatus") == "LinkUp"
                        and (port_id := _port_id(port)) is not None
                    ]
                },
            )
        else:
            yield Service(item=section[key]["Id"])


def _physical_ports(adapter: RedfishAPIData) -> Sequence[RedfishAPIData]:
    ports = adapter.get("PhysicalPorts")
    return ports if isinstance(ports, list) else []


def _port_id(port: RedfishAPIData) -> str | None:
    return port.get("MacAddress") or port.get("Name")


def _check_ports(ports: Sequence[RedfishAPIData], discovered_ports: Sequence[str]) -> CheckResult:
    not_monitored = []
    reported_ports = set()
    for port in ports:
        name = str(port.get("Name") or port.get("MacAddress") or "port without MAC or name")
        link_status = port.get("LinkStatus")
        port_id = _port_id(port)
        reported_ports.add(port_id)
        if port_id not in discovered_ports:
            if link_status != "LinkUp":
                not_monitored.append(name)
            elif port_id is None:
                yield Result(
                    state=State.WARN,
                    summary="Port without MAC or name: LinkUp but cannot be monitored",
                )
            else:
                yield Result(
                    state=State.WARN,
                    summary=f"Port {name}: LinkUp but not monitored, rediscover the service",
                )
            continue
        if link_status != "LinkUp":
            yield Result(
                state=State.CRIT,
                summary=f"Port {name}: {link_status or 'no link status'} (was LinkUp at discovery)",
            )
            continue
        port_state, port_msg = redfish_health_state(port.get("Status", {}))
        yield Result(state=State(port_state), notice=f"Port {name}: {port_msg}")

    for port_id in discovered_ports:
        if port_id not in reported_ports:
            yield Result(
                state=State.CRIT,
                summary=f"Port {port_id}: not reported (was LinkUp at discovery)",
            )

    if not_monitored:
        yield Result(state=State.OK, notice=f"Not monitored: {', '.join(not_monitored)}")


def _adapter_status(
    status: RedfishAPIData, unmonitored_ports: Sequence[RedfishAPIData]
) -> Iterable[tuple[State, str]]:
    worst_unmonitored = max(
        (
            redfish_health_state({"Health": port.get("Status", {}).get("Health")})[0]
            for port in unmonitored_ports
        ),
        default=0,
    )
    adapter_health, health_msg = redfish_health_state({"Health": status.get("Health")})
    # the health gives no cause, so a real fault matching an unused port is hidden too
    if adapter_health in (State.WARN.value, State.CRIT.value) and (
        adapter_health == worst_unmonitored
    ):
        dev_state, dev_msg = redfish_health_state(
            {k: v for k, v in status.items() if k != "Health"}
        )
        yield State(dev_state), dev_msg
        yield State.OK, f"{health_msg} (ignored, unmonitored ports report the same)"
        return

    dev_state, dev_msg = redfish_health_state(status)
    yield State(dev_state), dev_msg


def check_redfish_networkadapters(
    item: str, params: Mapping[str, Sequence[str]], section: RedfishAPIData
) -> CheckResult:
    data = section.get(item, None)
    if data is None:
        return

    model = data.get("Model", data.get("Name"))
    if model:
        yield Result(
            state=State.OK,
            summary=(
                f"Model: {model}, "
                f"SeNr: {data.get('SerialNumber')}, PartNr: {data.get('PartNumber')}"
            ),
        )

    unmonitored_ports = []
    if (discovered_ports := params.get("discovered_ports")) is not None:
        ports = _physical_ports(data)
        yield from _check_ports(ports, discovered_ports)
        unmonitored_ports = [p for p in ports if _port_id(p) not in discovered_ports]

    for state, message in _adapter_status(data.get("Status", {}), unmonitored_ports):
        yield Result(state=state, notice=message) if model else Result(state=state, summary=message)


check_plugin_redfish_networkadapters = CheckPlugin(
    name="redfish_networkadapters",
    service_name="Network adapter %s",
    sections=["redfish_networkadapters"],
    discovery_function=discovery_redfish_networkadapters,
    check_function=check_redfish_networkadapters,
    check_default_parameters={},
)
