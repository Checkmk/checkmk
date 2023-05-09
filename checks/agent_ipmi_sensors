#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from itertools import chain
from typing import Any, Mapping, Optional, Sequence

from cmk.base.check_api import passwordstore_get_cmdline
from cmk.base.config import special_agent_info

_DEFAULT_OPTIONS = {
    "quiet_cache": False,
    "sdr_cache_recreate": False,
    "interpret_oem_data": False,
    "output_sensor_state": True,
    "ignore_not_available_sensors": False,
    "output_sensor_thresholds": False,
}


def agent_ipmi_sensors_arguments(
    params: tuple[str, Mapping[str, Any]], hostname: str, ipaddress: Optional[str]
) -> Sequence[str | tuple[str, str, str]]:
    ipmi_command, options = params
    return [
        ipaddress or hostname,
        options["username"],
        passwordstore_get_cmdline("%s", options["password"]),
        ipmi_command,
        options["privilege_lvl"],
        *(_ipmitool_args(options) if ipmi_command == "ipmitool" else _freeipmi_args(options)),
    ]


def _ipmitool_args(options: Mapping[str, Any]) -> Iterable[str]:
    if not (value := options.get("intf")):
        return
    yield from ("--intf", value)


def _freeipmi_args(options: Mapping[str, Any]) -> Iterable[str]:
    yield from chain.from_iterable(
        (
            opt,
            value,
        )
        for opt, parameter in [
            ("--driver", "ipmi_driver"),
            ("--driver_type", "driver_type"),
            ("--key", "BMC_key"),
        ]
        if (value := options.get(parameter))
    )
    yield from (
        flag
        for flag, checkbox in [
            ("--quiet_cache", "quiet_cache"),
            ("--sdr_cache_recreate", "sdr_cache_recreate"),
            ("--interpret_oem_data", "interpret_oem_data"),
            ("--output_sensor_state", "output_sensor_state"),
            ("--ignore_not_available_sensors", "ignore_not_available_sensors"),
            ("--output_sensor_thresholds", "output_sensor_thresholds"),
        ]
        if options.get(checkbox, _DEFAULT_OPTIONS[checkbox])
    )


special_agent_info["ipmi_sensors"] = agent_ipmi_sensors_arguments
