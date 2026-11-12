#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
    Metric,
)


class Device(BaseModel, frozen=True):
    name: str
    status: str
    type: str
    details: str | None = None
    model: str | None = None
    voltage: int | None = None
    model: str | None = None
    serial: str | None = None


class Hardware(BaseModel, frozen=True):
    storage_bays: Mapping[str, Device]
    ethernet_ports: Mapping[str, Device]
    fibre_channel_ports: Mapping[str, Device]
    infiniband_ports: Mapping[str, Device]
    fans: Mapping[str, Device]
    power_supply: Mapping[str, Device]
    chassis: Mapping[str, Device]


MAP_DEVICE_STATUS = {
    "ok": State.OK,
    "healthy": State.OK,
    "unused": State.OK,
    "unknown": State.WARN,
    "identifying": State.WARN,
    "critical": State.CRIT,
    "unhealthy": State.CRIT,
    "not_installed": State.OK,
}


def parse_hardware(string_table: StringTable) -> Hardware | None:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None

    devices = [Device.model_validate(item) for item in json_data["items"]]

    return Hardware(
        storage_bays={d.name: d for d in devices if d.type == "drive_bay"},
        ethernet_ports={d.name: d for d in devices if d.type == "eth_port"},
        fibre_channel_ports={d.name: d for d in devices if d.type == "fc_port"},
        infiniband_ports={d.name: d for d in devices if d.type == "ib_port"},
        fans={d.name: d for d in devices if d.type == "cooling"},
        power_supply={d.name: d for d in devices if d.type == "power_supply"},
        chassis={d.name: d for d in devices if d.type == "chassis"},
    )


agent_section_pure_storage_fa_hardware = AgentSection(
    name="pure_storage_fa_hardware",
    parse_function=parse_hardware,
)


def check_device(device: Device) -> CheckResult:
    state = MAP_DEVICE_STATUS.get(device.status, State.CRIT)
    yield Result(state=state, summary=f"Status: {device.status}")

    if device.details:
        yield Result(state=State.OK, summary=device.details)


#   .--Storage Bay---------------------------------------------------------.
#   |       ____  _                               ____                     |
#   |      / ___|| |_ ___  _ __ __ _  __ _  ___  | __ )  __ _ _   _        |
#   |      \___ \| __/ _ \| '__/ _` |/ _` |/ _ \ |  _ \ / _` | | | |       |
#   |       ___) | || (_) | | | (_| | (_| |  __/ | |_) | (_| | |_| |       |
#   |      |____/ \__\___/|_|  \__,_|\__, |\___| |____/ \__,_|\__, |       |
#   |                                |___/                    |___/        |
#   '----------------------------------------------------------------------'
# .


def discover_storage_bay(section: Hardware) -> DiscoveryResult:
    for item in section.storage_bays:
        yield Service(item=item)


def check_storage_bay(item: str, section: Hardware) -> CheckResult:
    if (storage_bay := section.storage_bays.get(item)) is None:
        return

    yield from check_device(storage_bay)


check_plugin_pure_storage_storage_bay = CheckPlugin(
    name="pure_storage_storage_bay",
    sections=["pure_storage_fa_hardware"],
    service_name="Storage Bay %s",
    discovery_function=discover_storage_bay,
    check_function=check_storage_bay,
)

#   .--Ethernet Port-------------------------------------------------------.
#   |   _____ _   _                          _     ____            _       |
#   |  | ____| |_| |__   ___ _ __ _ __   ___| |_  |  _ \ ___  _ __| |_     |
#   |  |  _| | __| '_ \ / _ \ '__| '_ \ / _ \ __| | |_) / _ \| '__| __|    |
#   |  | |___| |_| | | |  __/ |  | | | |  __/ |_  |  __/ (_) | |  | |_     |
#   |  |_____|\__|_| |_|\___|_|  |_| |_|\___|\__| |_|   \___/|_|   \__|    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


def discover_ethernet_port(section: Hardware) -> DiscoveryResult:
    for item in section.ethernet_ports:
        yield Service(item=item)


def check_ethernet_port(item: str, section: Hardware) -> CheckResult:
    if (ethernet_port := section.ethernet_ports.get(item)) is None:
        return

    yield from check_device(ethernet_port)


check_plugin_pure_storage_ethernet_port = CheckPlugin(
    name="pure_storage_ethernet_port",
    sections=["pure_storage_fa_hardware"],
    service_name="Ethernet Port %s",
    discovery_function=discover_ethernet_port,
    check_function=check_ethernet_port,
)

#   .--Fibre Channel Port--------------------------------------------------.
#   |    _____ _ _                 ____ _                            _     |
#   |   |  ___(_) |__  _ __ ___   / ___| |__   __ _ _ __  _ __   ___| |    |
#   |   | |_  | | '_ \| '__/ _ \ | |   | '_ \ / _` | '_ \| '_ \ / _ \ |    |
#   |   |  _| | | |_) | | |  __/ | |___| | | | (_| | | | | | | |  __/ |    |
#   |   |_|   |_|_.__/|_|  \___|  \____|_| |_|\__,_|_| |_|_| |_|\___|_|    |
#   |                                                                      |
#   |                         ____            _                            |
#   |                        |  _ \ ___  _ __| |_                          |
#   |                        | |_) / _ \| '__| __|                         |
#   |                        |  __/ (_) | |  | |_                          |
#   |                        |_|   \___/|_|   \__|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


def discover_fibre_channel_port(section: Hardware) -> DiscoveryResult:
    for item in section.fibre_channel_ports:
        yield Service(item=item)


def check_fibre_channel_port(item: str, section: Hardware) -> CheckResult:
    if (fibre_channel_port := section.fibre_channel_ports.get(item)) is None:
        return

    yield from check_device(fibre_channel_port)


check_plugin_pure_storage_fibre_channel_port = CheckPlugin(
    name="pure_storage_fibre_channel_port",
    sections=["pure_storage_fa_hardware"],
    service_name="Fibre Channel Port %s",
    discovery_function=discover_fibre_channel_port,
    check_function=check_fibre_channel_port,
)

#   .--InfiniBand Port-----------------------------------------------------.
#   |           ___        __ _       _ ____                  _            |
#   |          |_ _|_ __  / _(_)_ __ (_) __ )  __ _ _ __   __| |           |
#   |           | || '_ \| |_| | '_ \| |  _ \ / _` | '_ \ / _` |           |
#   |           | || | | |  _| | | | | | |_) | (_| | | | | (_| |           |
#   |          |___|_| |_|_| |_|_| |_|_|____/ \__,_|_| |_|\__,_|           |
#   |                                                                      |
#   |                         ____            _                            |
#   |                        |  _ \ ___  _ __| |_                          |
#   |                        | |_) / _ \| '__| __|                         |
#   |                        |  __/ (_) | |  | |_                          |
#   |                        |_|   \___/|_|   \__|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


def discover_infiniband_port(section: Hardware) -> DiscoveryResult:
    for item in section.infiniband_ports:
        yield Service(item=item)


def check_infiniband_port(item: str, section: Hardware) -> CheckResult:
    if (infiniband_port := section.infiniband_ports.get(item)) is None:
        return

    yield from check_device(infiniband_port)


check_plugin_pure_storage_infiniband_port = CheckPlugin(
    name="pure_storage_infiniband_port",
    sections=["pure_storage_fa_hardware"],
    service_name="InfiniBand Port %s",
    discovery_function=discover_infiniband_port,
    check_function=check_infiniband_port,
)

#   .--Fan-----------------------------------------------------------------.
#   |                           _____                                      |
#   |                          |  ___|_ _ _ __                             |
#   |                          | |_ / _` | '_ \                            |
#   |                          |  _| (_| | | | |                           |
#   |                          |_|  \__,_|_| |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# .


def discover_fan(section: Hardware) -> DiscoveryResult:
    for item in section.fans:
        yield Service(item=item)


def check_fan(item: str, section: Hardware) -> CheckResult:
    if (fan := section.fans.get(item)) is None:
        return

    yield from check_device(fan)


check_plugin_pure_storage_fan = CheckPlugin(
    name="pure_storage_fan",
    sections=["pure_storage_fa_hardware"],
    service_name="Fan %s",
    discovery_function=discover_fan,
    check_function=check_fan,
)


def discover_power_supply(section: Hardware) -> DiscoveryResult:
    for item in section.power_supply:
        yield Service(item=item)


def check_power_supply(item: str, section: Hardware) -> CheckResult:
    if (power_supply := section.power_supply.get(item)) is None:
        return
    state = State.UNKNOWN
    summary = "Check failed"
    if power_supply.status == "ok":
        state = State.OK
        summary = f"{power_supply.name} (Model {power_supply.model}) is running with {power_supply.voltage} Volt"
    elif int(power_supply.voltage) < 50:
        state = State.WARN
        summary = (
            f"{power_supply.name} is running with only {power_supply.voltage} Volt"
        )
        if int(power_supply.voltage) < 10:
            state = State.CRIT
    else:
        state = State.CRIT
        summary = f"{power_supply.name} (Model {power_supply.model}) has state {power_supply.status} with {power_supply.voltage} Volt (could not set state)"
    yield Metric("pure_storage_fa_power_supply", int(power_supply.voltage))
    yield Result(state=state, summary=summary)


check_plugin_pure_storage_fa_power_supply = CheckPlugin(
    name="pure_storage_fa_power_supply",
    sections=["pure_storage_fa_hardware"],
    service_name="Power Supply %s",
    discovery_function=discover_power_supply,
    check_function=check_power_supply,
)


def discover_serial_chassis(section: Hardware) -> DiscoveryResult:
    if section.chassis:
        yield Service()


def check_serial_chassis(section: Hardware) -> CheckResult:
    if (chassis := section.chassis.get("CH0")) is None:
        return
    yield Result(
        state=State.OK,
        summary=f"{chassis.name}, Model: {chassis.model}, Serial: {chassis.serial}",
    )


check_plugin_pure_storage_fa_serial_chassis = CheckPlugin(
    name="pure_storage_fa_serial_chassis",
    sections=["pure_storage_fa_hardware"],
    service_name="Chassis Serial Number",
    discovery_function=discover_serial_chassis,
    check_function=check_serial_chassis,
)
