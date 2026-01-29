#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# <<<scaleio_devices>>>
# DEVICE 123:
#   ID                  Foo
#   SDS_ID              Bar
#   STORAGE_POOL_ID     123
#   STATE               DEVICE_NORMAL
#   ERR_STATE           NO_ERROR


# mypy: disable-error-code="var-annotated"

from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.agent_based.v2 import StringTable

check_info = {}


def parse_scaleio_devices(string_table: StringTable) -> Mapping[str, list[dict[str, str]]]:
    devices = {}
    device = {}
    for line in string_table:
        if len(line) != 2:
            continue
        key, value = line
        if key == "DEVICE":
            # value ends with ":"
            device_id = value[:-1]
            device = devices.setdefault(device_id, {key: device_id})
        elif device:
            device[key] = value

    parsed = {}
    for attrs in devices.values():
        parsed.setdefault(attrs["SDS_ID"], []).append(attrs)
    return parsed


def _make_state_readable(raw_state: str) -> str:
    return raw_state.replace("_", " ").lower()


def check_scaleio_devices(
    item: str, params: Mapping[str, Any], parsed: Mapping[str, list[dict[str, str]]]
) -> LegacyCheckResult:
    if not (devices := parsed.get(item)):
        return
    num_devices = len(devices)
    error_devices = []
    long_output = []
    for device in devices:
        err_state = device.get("ERR_STATE", "n/a")
        if err_state == "NO_ERROR":
            continue
        err_state_readable = _make_state_readable(err_state)
        dev_id = device["DEVICE"]
        error_devices.append(dev_id)
        long_output.append(
            "Device %s: Error: %s, State: %s (ID: %s, Storage pool ID: %s)"
            % (
                dev_id,
                _make_state_readable(device.get("STATE", "n/a")),
                err_state_readable,
                dev_id,
                device.get("STORAGE_POOL_ID", "n/a"),
            )
        )

    if error_devices:
        num_errors = len(error_devices)
        yield 2, "%d devices, %d errors (%s)" % (num_devices, num_errors, ", ".join(error_devices))
    else:
        yield 0, "%d devices, no errors" % num_devices

    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


def discover_scaleio_devices(
    section: Mapping[str, list[dict[str, str]]],
) -> Iterable[tuple[str, dict[str, Any]]]:
    yield from ((item, {}) for item in section)


check_info["scaleio_devices"] = LegacyCheckDefinition(
    name="scaleio_devices",
    parse_function=parse_scaleio_devices,
    service_name="ScaleIO Data Server %s Devices",
    discovery_function=discover_scaleio_devices,
    check_function=check_scaleio_devices,
)
