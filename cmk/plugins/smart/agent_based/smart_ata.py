#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import MutableMapping
from typing import Literal, Required, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_rate,
    get_value_store,
    Metric,
    NoLevelsT,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

from .smart_posix import ATAAll, ATADevice, Section

MAX_COMMAND_TIMEOUTS_PER_HOUR = 100


def discovery_smart_ata_temp(
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for item, disk in devices.items():
        if isinstance(disk.device, ATADevice) and disk.temperature is not None:
            yield Service(
                item=item,
                labels=[
                    ServiceLabel("cmk/smart/type", "ATA"),
                    ServiceLabel("cmk/smart/device", disk.device.name),
                    ServiceLabel("cmk/smart/model", disk.model_name),
                    ServiceLabel("cmk/smart/serial", disk.serial_number),
                ],
            )


def check_smart_ata_temp(
    item: str,
    params: TempParamDict,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> CheckResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    if not isinstance(disk := devices.get(item), ATAAll) or disk.temperature is None:
        return

    yield from check_temperature(
        reading=disk.temperature.current,
        params=params,
        unique_name=f"smart_{item}",
        value_store=get_value_store(),
    )


check_plugin_smart_ata_temp = CheckPlugin(
    name="smart_ata_temp",
    sections=["smart_posix_all", "smart_posix_scan_arg"],
    service_name="Temperature SMART %s",
    discovery_function=discovery_smart_ata_temp,
    check_function=check_smart_ata_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)


type AtaLevels = (
    tuple[Literal["levels_upper"], FixedLevelsT[int] | NoLevelsT]
    | tuple[Literal["discovered_value"], None]
)


class AtaDiscoveredParams(TypedDict):
    id_5: Required[int | None]
    id_10: Required[int | None]
    id_184: Required[int | None]
    id_187: Required[int | None]
    id_188: Required[int | None]
    id_196: Required[int | None]
    id_197: Required[int | None]
    id_199: Required[int | None]


class AtaRuleSetParams(TypedDict):
    levels_5: AtaLevels
    levels_10: AtaLevels
    levels_184: AtaLevels
    levels_187: AtaLevels
    levels_196: AtaLevels
    levels_197: AtaLevels
    levels_199: AtaLevels


class AtaParams(AtaRuleSetParams, AtaDiscoveredParams):
    pass


DEFAULT_PARAMS: AtaRuleSetParams = {
    "levels_5": ("discovered_value", None),
    "levels_10": ("discovered_value", None),
    "levels_184": ("discovered_value", None),
    "levels_187": ("discovered_value", None),
    "levels_196": ("discovered_value", None),
    "levels_197": ("discovered_value", None),
    "levels_199": ("discovered_value", None),
}


def discover_smart_ata(
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for item, disk in devices.items():
        if isinstance(disk.device, ATADevice) and disk.ata_smart_attributes is not None:
            parameters: AtaDiscoveredParams = {
                "id_5": entry.raw.value if (entry := disk.by_id(5)) is not None else None,
                "id_10": entry.raw.value if (entry := disk.by_id(10)) is not None else None,
                "id_184": entry.raw.value if (entry := disk.by_id(184)) is not None else None,
                "id_187": entry.raw.value if (entry := disk.by_id(187)) is not None else None,
                "id_188": entry.raw.value if (entry := disk.by_id(188)) is not None else None,
                "id_196": entry.raw.value if (entry := disk.by_id(196)) is not None else None,
                "id_197": entry.raw.value if (entry := disk.by_id(197)) is not None else None,
                "id_199": entry.raw.value if (entry := disk.by_id(199)) is not None else None,
            }
            yield Service(
                item=item,
                labels=[
                    ServiceLabel("cmk/smart/type", "ATA"),
                    ServiceLabel("cmk/smart/device", disk.device.name),
                    ServiceLabel("cmk/smart/model", disk.model_name),
                    ServiceLabel("cmk/smart/serial", disk.serial_number),
                ],
                parameters=parameters,
            )


def check_smart_ata(
    item: str,
    params: AtaParams,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> CheckResult:
    yield from _check_smart_ata(
        item,
        params,
        section_smart_posix_all,
        section_smart_posix_scan_arg,
        get_value_store(),
        time.time(),
    )


def _check_smart_ata(
    item: str,
    params: AtaParams,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    if not isinstance(disk := devices.get(item), ATAAll):
        return

    if (reallocated_sector_count := disk.by_id(5)) is not None:
        yield from _check_against_params(
            param=params["levels_5"],
            value=reallocated_sector_count.raw.value,
            discovered_value=params.get("id_5"),
            label="Reallocated sectors",
            metric_name="harddrive_reallocated_sectors",
        )

    if (power_on_hours := disk.by_id(9)) is not None:
        yield from check_levels(
            value=power_on_hours.raw.value * 3600,
            label="Powered on",
            render_func=render.timespan,
            metric_name="uptime",
        )

    if (spin_retries := disk.by_id(10)) is not None:
        yield from _check_against_params(
            param=params["levels_10"],
            value=spin_retries.raw.value,
            discovered_value=params.get("id_10"),
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
        yield from _check_against_params(
            param=params["levels_184"],
            value=end_to_end_errors.raw.value,
            discovered_value=params.get("id_184"),
            label="End-to-End Errors",
            metric_name="harddrive_end_to_end_errors",
        )

    if (uncorrectable_errors := disk.by_id(187)) is not None:
        yield from _check_against_params(
            param=params["levels_187"],
            value=uncorrectable_errors.raw.value,
            discovered_value=params.get("id_187"),
            label="Uncorrectable errors",
            metric_name="harddrive_uncorrectable_errors",
        )

    yield from _check_command_timeout(disk, value_store, now)

    if (reallocated_events := disk.by_id(196)) is not None:
        yield from _check_against_params(
            param=params["levels_196"],
            value=reallocated_events.raw.value,
            discovered_value=params.get("id_196"),
            label="Reallocated events",
            metric_name="harddrive_reallocated_events",
        )
        yield from check_levels(
            value=reallocated_events.value,
            levels_lower=("fixed", (reallocated_events.thresh, reallocated_events.thresh)),
            label="Normalized value",
        )

    if (pending_sectors := disk.by_id(197)) is not None:
        yield from _check_against_params(
            param=params["levels_197"],
            value=pending_sectors.raw.value,
            discovered_value=params.get("id_197"),
            label="Pending sectors",
            metric_name="harddrive_pending_sectors",
        )

    if (crc_errors := disk.by_id(199)) is not None:
        if crc_errors.name == "UDMA_CRC_Error_Count":
            yield from _check_against_params(
                param=params["levels_199"],
                value=crc_errors.raw.value,
                discovered_value=params.get("id_199"),
                label="UDMA CRC errors",
                metric_name="harddrive_udma_crc_errors",
            )
        else:
            yield from _check_against_params(
                param=params["levels_199"],
                value=crc_errors.raw.value,
                discovered_value=params.get("id_199"),
                label="CRC errors",
                metric_name="harddrive_crc_errors",
            )


def _check_against_params(
    param: AtaLevels, value: int, discovered_value: int | None, label: str, metric_name: str
) -> CheckResult:
    match param[1]:
        case None:
            yield from _check_against_discovery(value, discovered_value, label, metric_name)
        case levels_upper:
            yield from check_levels(
                value=value,
                levels_upper=levels_upper,
                label=label,
                render_func=str,
                metric_name=metric_name,
            )


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
                f"(counter increased more than {MAX_COMMAND_TIMEOUTS_PER_HOUR} counts / h (!!))",
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Command Timeout Counter: {command_timeout_counter.raw.value}",
            )
        yield Metric("harddrive_cmd_timeouts", command_timeout_counter.raw.value)


check_plugin_smart_ata_stats = CheckPlugin(
    name="smart_ata_stats",
    sections=[
        "smart_posix_all",
        "smart_posix_scan_arg",
    ],
    service_name="SMART %s Stats",
    discovery_function=discover_smart_ata,
    check_function=check_smart_ata,
    check_ruleset_name="smart_ata",
    check_default_parameters=DEFAULT_PARAMS,
)
