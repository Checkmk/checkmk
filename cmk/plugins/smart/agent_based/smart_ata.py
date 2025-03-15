#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

from .smart_posix import ATAAll, ATADevice, Section

MAX_COMMAND_TIMEOUTS_PER_HOUR = 100


def discovery_smart_ata_temp(section: Section) -> DiscoveryResult:
    for disk in section:
        if isinstance(disk.device, ATADevice) and disk.temperature is not None:
            yield Service(item=disk.device.name)


def check_smart_ata_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (disk := _get_disk_ata(section, item)) is None:
        return

    if disk.temperature is None:
        return

    yield from check_temperature(
        reading=disk.temperature.current,
        params=params,
        unique_name=f"smart_{item}",
        value_store=get_value_store(),
    )


check_plugin_smart_ata_temp = CheckPlugin(
    name="smart_ata_temp",
    sections=["smart_posix_all"],
    service_name="Temperature SMART %s",
    discovery_function=discovery_smart_ata_temp,
    check_function=check_smart_ata_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)


def discover_smart_ata(section: Section) -> DiscoveryResult:
    for disk in section:
        if isinstance(disk.device, ATADevice) and disk.ata_smart_attributes is not None:
            yield Service(
                item=disk.device.name,
                parameters={
                    str(id_): entry.raw.value
                    for id_ in [5, 10, 184, 187, 188, 197, 199]
                    if (entry := disk.by_id(id_)) is not None
                },
            )


def check_smart_ata(item: str, params: Mapping[str, int | None], section: Section) -> CheckResult:
    yield from _check_smart_ata(item, params, section, get_value_store(), time.time())


def _check_smart_ata(
    item: str,
    params: Mapping[str, int | None],
    section: Section,
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    if (disk := _get_disk_ata(section, item)) is None:
        return

    if (reallocated_sector_count := disk.by_id(5)) is not None:
        yield from _check_against_discovery(
            value=reallocated_sector_count.raw.value,
            discovered_value=params.get("5"),
            label="Reallocated sectors",
            metric_name="harddrive_reallocated_sectors",
        )

    if (power_on_hours := disk.by_id(9)) is not None:
        yield from check_levels(
            value=power_on_hours.raw.value,
            label="Powered on",
            render_func=render.timespan,
            metric_name="uptime",
        )

    if (spin_retries := disk.by_id(10)) is not None:
        yield from _check_against_discovery(
            value=spin_retries.raw.value,
            discovered_value=params.get("10"),
            label="Spin retries",
            metric_name="harddrive_spin_retries",
        )

    if (power_cycles := disk.by_id(12)) is not None:
        yield from check_levels(
            value=power_cycles.raw.value,
            label="Power cycles",
            metric_name="harddrive_power_cycles",
            render_func=str,
        )

    if (end_to_end_errors := disk.by_id(184)) is not None:
        yield from _check_against_discovery(
            value=end_to_end_errors.raw.value,
            discovered_value=params.get("184"),
            label="End-to-End Errors",
            metric_name="harddrive_end_to_end_errors",
        )

    if (uncorrectable_errors := disk.by_id(187)) is not None:
        yield from _check_against_discovery(
            value=uncorrectable_errors.raw.value,
            discovered_value=params.get("187"),
            label="Uncorrectable errors",
            metric_name="harddrive_uncorrectable_errors",
        )

    yield from _check_command_timeout(disk, value_store, now)

    if (reallocated_events := disk.by_id(196)) is not None:
        yield from _check_against_discovery(
            value=reallocated_events.raw.value,
            discovered_value=params.get("196"),
            label="Reallocated events",
            metric_name="harddrive_reallocated_events",
        )
        yield from check_levels(
            value=reallocated_events.value,
            levels_lower=("fixed", (reallocated_events.thresh, reallocated_events.thresh)),
            label="Normalized value",
        )

    if (pending_sectors := disk.by_id(197)) is not None:
        yield from _check_against_discovery(
            value=pending_sectors.raw.value,
            discovered_value=params.get("197"),
            label="Pending sectors",
            metric_name="harddrive_pending_sectors",
        )

    if (crc_errors := disk.by_id(199)) is not None:
        if crc_errors.name == "UDMA_CRC_Error_Count":
            yield from _check_against_discovery(
                value=crc_errors.raw.value,
                discovered_value=params.get("199"),
                label="UDMA CRC errors",
                metric_name="harddrive_udma_crc_errors",
            )
        else:
            yield from _check_against_discovery(
                value=crc_errors.raw.value,
                discovered_value=params.get("199"),
                label="CRC errors",
                metric_name="harddrive_crc_errors",
            )


def _get_disk_ata(section: Section, item: str) -> ATAAll | None:
    for d in section:
        if isinstance(d.device, ATADevice) and d.device.name == item:
            return d

    return None


def _check_against_discovery(
    value: int, discovered_value: int | None, label: str, metric_name: str
) -> CheckResult:
    if discovered_value is not None and value > discovered_value:
        yield Result(
            state=State.CRIT,
            summary=f"{label}: {value} (during discovery: {discovered_value}) (!!)",
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"{label}: {value}",
        )
    yield Metric(metric_name, value)


def _check_command_timeout(
    disk: ATAAll, value_store: MutableMapping[str, object], now: float
) -> CheckResult:
    if (command_timeout_counter := disk.by_id(188)) is not None:
        rate = get_rate(value_store, "cmd_timeout", now, command_timeout_counter.raw.value)
        if rate >= MAX_COMMAND_TIMEOUTS_PER_HOUR / (60 * 60):
            yield Result(
                state=State.CRIT,
                summary=f"Command Timeout Counter: {command_timeout_counter.raw.value} "
                "(counter increased more than {MAX_COMMAND_TIMEOUTS_PER_HOUR} counts / h (!!))",
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Command Timeout Counter: {command_timeout_counter.raw.value}",
            )
        yield Metric("harddrive_cmd_timeouts", command_timeout_counter.raw.value)


check_plugin_smart_ata_stats = CheckPlugin(
    name="smart_ata_stats",
    sections=["smart_posix_all"],
    service_name="SMART %s Stats",
    discovery_function=discover_smart_ata,
    check_function=check_smart_ata,
    check_default_parameters={},  # needed to pass discovery parameters along!
)
