#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.lib.temperature import check_temperature, TempParamType

from .smart_posix import NVMeAll, NVMeDevice, Section


def discovery_smart_nvme_temp(section: Section) -> DiscoveryResult:
    for disk in section:
        if (
            isinstance(disk.device, NVMeDevice)
            and disk.nvme_smart_health_information_log is not None
        ):
            yield Service(item=disk.device.name)


def check_smart_nvme_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (disk := _get_disk_nvme(section, item)) is None:
        return

    if (
        disk.nvme_smart_health_information_log is None
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
    sections=["smart_posix_all"],
    service_name="Temperature SMART %s",
    discovery_function=discovery_smart_nvme_temp,
    check_function=check_smart_nvme_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)


def discover_smart_nvme(section: Section) -> DiscoveryResult:
    for disk in section:
        if (
            isinstance(disk.device, NVMeDevice)
            and disk.nvme_smart_health_information_log is not None
        ):
            yield Service(
                item=disk.device.name,
                parameters={
                    "critical_warning": disk.nvme_smart_health_information_log.critical_warning,
                    "media_errors": disk.nvme_smart_health_information_log.media_errors,
                },
            )


def check_smart_nvme(item: str, params: Mapping[str, int], section: Section) -> CheckResult:
    if (disk := _get_disk_nvme(section, item)) is None:
        return

    if disk.nvme_smart_health_information_log is None:
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


def _get_disk_nvme(section: Section, item: str) -> NVMeAll | None:
    for d in section:
        if isinstance(d.device, NVMeDevice) and d.device.name == item:
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


check_plugin_smart_nvme_stats = CheckPlugin(
    name="smart_nvme_stats",
    sections=["smart_posix_all"],
    service_name="SMART %s Stats",
    discovery_function=discover_smart_nvme,
    check_function=check_smart_nvme,
    check_default_parameters={},  # needed to pass discovery parameters along!
)
