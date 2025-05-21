#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, Required, TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
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

from .smart_posix import NVMeAll, NVMeDevice, Section


def discovery_smart_nvme_temp(
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for item, disk in devices.items():
        if (
            isinstance(disk.device, NVMeDevice)
            and disk.nvme_smart_health_information_log is not None
        ):
            yield Service(
                item=item,
                labels=[
                    ServiceLabel("cmk/smart/type", "NVMe"),
                    ServiceLabel("cmk/smart/device", disk.device.name),
                    ServiceLabel("cmk/smart/model", disk.model_name),
                    ServiceLabel("cmk/smart/serial", disk.serial_number),
                ],
            )


def check_smart_nvme_temp(
    item: str,
    params: TempParamDict,
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> CheckResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    if (
        not isinstance(disk := devices.get(item), NVMeAll)
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
    check_function=check_smart_nvme_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)


type DiscoveredOrLevels = (
    tuple[Literal["levels_upper"], FixedLevelsT[int] | NoLevelsT]
    | tuple[Literal["discovered_value"], None]
)

type AvailableSpareLevels = (
    tuple[Literal["levels_lower"], FixedLevelsT[int] | NoLevelsT]
    | tuple[Literal["threshold"], None]
)


class NVMeRuleSetParams(TypedDict):
    levels_critical_warning: DiscoveredOrLevels
    levels_media_errors: DiscoveredOrLevels
    levels_available_spare: AvailableSpareLevels
    levels_spare_percentage_used: FixedLevelsT[int] | NoLevelsT
    levels_error_information_log_entries: FixedLevelsT[int] | NoLevelsT
    levels_data_units_read: FixedLevelsT[int] | NoLevelsT
    levels_data_units_written: FixedLevelsT[int] | NoLevelsT


class NVMeDiscoveredParams(TypedDict):
    critical_warning: Required[int]
    media_errors: Required[int]


class NVMeParams(NVMeRuleSetParams, NVMeDiscoveredParams):
    pass


DEFAULT_PARAMS: NVMeRuleSetParams = {
    "levels_critical_warning": ("discovered_value", None),
    "levels_media_errors": ("discovered_value", None),
    "levels_available_spare": ("threshold", None),
    "levels_spare_percentage_used": ("no_levels", None),
    "levels_error_information_log_entries": ("no_levels", None),
    "levels_data_units_read": ("no_levels", None),
    "levels_data_units_written": ("no_levels", None),
}


def discover_smart_nvme(
    section_smart_posix_all: Section | None,
    section_smart_posix_scan_arg: Section | None,
) -> DiscoveryResult:
    devices = {
        **(section_smart_posix_scan_arg.devices if section_smart_posix_scan_arg else {}),
        **(section_smart_posix_all.devices if section_smart_posix_all else {}),
    }
    for item, disk in devices.items():
        if (
            isinstance(disk.device, NVMeDevice)
            and disk.nvme_smart_health_information_log is not None
        ):
            parameters: NVMeDiscoveredParams = {
                "critical_warning": disk.nvme_smart_health_information_log.critical_warning,
                "media_errors": disk.nvme_smart_health_information_log.media_errors,
            }
            yield Service(
                item=item,
                labels=[
                    ServiceLabel("cmk/smart/type", "NVMe"),
                    ServiceLabel("cmk/smart/device", disk.device.name),
                    ServiceLabel("cmk/smart/model", disk.model_name),
                    ServiceLabel("cmk/smart/serial", disk.serial_number),
                ],
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
        not isinstance(disk := devices.get(item), NVMeAll)
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

    yield from _check_against_discovered_or_levels(
        param=params["levels_critical_warning"],
        value=disk.nvme_smart_health_information_log.critical_warning,
        discovered_value=params["critical_warning"],
        label="Critical warning",
        metric_name="nvme_critical_warning",
    )

    yield from _check_against_discovered_or_levels(
        param=params["levels_media_errors"],
        value=disk.nvme_smart_health_information_log.media_errors,
        discovered_value=params["media_errors"],
        label="Media and data integrity errors",
        metric_name="nvme_media_and_data_integrity_errors",
    )

    yield from _check_available_spare(
        param=params["levels_available_spare"],
        value=disk.nvme_smart_health_information_log.available_spare,
        threshold=disk.nvme_smart_health_information_log.available_spare_threshold,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.percentage_used,
        levels_upper=params["levels_spare_percentage_used"],
        label="Percentage used",
        metric_name="nvme_spare_percentage_used",
        render_func=render.percent,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.num_err_log_entries,
        levels_upper=params["levels_error_information_log_entries"],
        label="Error information log entries",
        metric_name="nvme_error_information_log_entries",
        render_func=str,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.data_units_read * 512000,
        levels_upper=params["levels_data_units_read"],
        label="Data units read",
        metric_name="nvme_data_units_read",
        render_func=render.bytes,
    )

    yield from check_levels(
        value=disk.nvme_smart_health_information_log.data_units_written * 512000,
        levels_upper=params["levels_data_units_written"],
        label="Data units written",
        metric_name="nvme_data_units_written",
        render_func=render.bytes,
    )


def _check_against_discovered_or_levels(
    param: DiscoveredOrLevels,
    value: int,
    discovered_value: int | None,
    label: str,
    metric_name: str,
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


def _check_available_spare(param: AvailableSpareLevels, value: int, threshold: int) -> CheckResult:
    levels_or_thresh = param[1]
    yield from check_levels(
        value=value,
        levels_lower=(
            ("fixed", (threshold, threshold)) if levels_or_thresh is None else levels_or_thresh
        ),
        label="Available spare",
        metric_name="nvme_available_spare",
        render_func=render.percent,
    )


check_plugin_smart_nvme_stats = CheckPlugin(
    name="smart_nvme_stats",
    sections=["smart_posix_all", "smart_posix_scan_arg"],
    service_name="SMART %s Stats",
    discovery_function=discover_smart_nvme,
    check_function=check_smart_nvme,
    check_ruleset_name="smart_nvme",
    check_default_parameters=DEFAULT_PARAMS,
)
