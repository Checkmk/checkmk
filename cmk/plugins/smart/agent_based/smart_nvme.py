#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Required, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.temperature import check_temperature

from .smart import DiscoveryParam, get_item, TempAndDiscoveredParams
from .smart_posix import NVMeAll, NVMeDevice, Section


def discovery_smart_nvme_temp(
    params: DiscoveryParam,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for key, disk in devices.items():
        if (
            isinstance(disk.device, NVMeDevice)
            and disk.nvme_smart_health_information_log is not None
        ):
            yield Service(
                item=get_item(disk, params["item_type"][0]),
                parameters={"key": key},
            )


def check_smart_nvme_temp(
    item: str,
    params: TempAndDiscoveredParams,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> CheckResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    if (
        not isinstance(disk := devices.get(params["key"]), NVMeAll)
        or disk.nvme_smart_health_information_log is None
        or disk.nvme_smart_health_information_log.temperature is None
    ):
        return

    yield from check_temperature(
        reading=disk.nvme_smart_health_information_log.temperature,
        params=params,
        unique_name=f"smart_{item}",
        value_store=get_value_store(),
    )


check_plugin_smart_nvme_temp = CheckPlugin(
    name="smart_nvme_temp",
    sections=["smart_posix_all", "smart_posix_scan_arg"],
    service_name="Temperature SMART %s",
    discovery_function=discovery_smart_nvme_temp,
    discovery_ruleset_name="smart_nvme",
    discovery_default_parameters={"item_type": ("device_name", None)},
    check_function=check_smart_nvme_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)


class NVMeParams(TypedDict):
    key: Required[tuple[str, str]]
    critical_warning: Required[int]
    media_errors: Required[int]


def discover_smart_nvme(
    params: DiscoveryParam,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for key, disk in devices.items():
        if (
            isinstance(disk.device, NVMeDevice)
            and disk.nvme_smart_health_information_log is not None
        ):
            parameters: NVMeParams = {
                "key": key,
                "critical_warning": disk.nvme_smart_health_information_log.critical_warning,
                "media_errors": disk.nvme_smart_health_information_log.media_errors,
            }
            yield Service(
                item=get_item(disk, params["item_type"][0]),
                parameters=parameters,
            )


def check_smart_nvme(
    item: str,
    params: NVMeParams,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> CheckResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    if (
        not isinstance(disk := devices.get(params["key"]), NVMeAll)
        or disk.nvme_smart_health_information_log is None
    ):
        return

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.power_on_hours * 3600,
        label="Powered on",
        render_func=render.timespan,
        metric_name="uptime",
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.power_cycles,
        label="Power cycles",
        metric_name="harddrive_power_cycles",
        render_func=str,
    )

    yield from _check_against_discovery(
        value=disk.nvme_smart_health_information_log.critical_warning,
        discovered_value=params["critical_warning"],
        label="Critical warning",
        metric_name="nvme_critical_warning",
    )

    yield from _check_against_discovery(
        value=disk.nvme_smart_health_information_log.media_errors,
        discovered_value=params["media_errors"],
        label="Media and data integrity errors",
        metric_name="nvme_media_and_data_integrity_errors",
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.available_spare,
        levels_lower=(
            "fixed",
            (
                disk.nvme_smart_health_information_log.available_spare_threshold,
                disk.nvme_smart_health_information_log.available_spare_threshold,
            ),
        ),
        label="Available spare",
        metric_name="nvme_available_spare",
        render_func=render.percent,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.percentage_used,
        label="Percentage used",
        metric_name="nvme_spare_percentage_used",
        render_func=render.percent,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.num_err_log_entries,
        label="Error information log entries",
        metric_name="nvme_error_information_log_entries",
        render_func=str,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.data_units_read * 512000,
        label="Data units read",
        metric_name="nvme_data_units_read",
        render_func=render.bytes,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.data_units_written * 512000,
        label="Data units written",
        metric_name="nvme_data_units_written",
        render_func=render.bytes,
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


check_plugin_smart_nvme_stats = CheckPlugin(
    name="smart_nvme_stats",
    sections=["smart_posix_all", "smart_posix_scan_arg"],
    service_name="SMART %s Stats",
    discovery_function=discover_smart_nvme,
    discovery_ruleset_name="smart_nvme",
    discovery_default_parameters={"item_type": ("device_name", None)},
    check_function=check_smart_nvme,
    check_default_parameters={},  # needed to pass discovery parameters along!
)
