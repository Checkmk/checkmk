#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from itertools import chain
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig
from cmk.server_side_calls.v1._utils import Secret


class _IPMIToolParams(BaseModel, frozen=True):
    username: str
    password: Secret
    privilege_lvl: Literal["callback", "user", "operator", "administrator"]
    intf: Literal["open", "lan", "lanplus", "imb"] | None = None


class _FreeIPMIParams(BaseModel, frozen=True):
    username: str
    password: Secret
    privilege_lvl: Literal["user", "operator", "admin"]
    ipmi_driver: str | None = None
    driver_type: str | None = None
    quiet_cache: bool = False
    sdr_cache_recreate: bool = False
    interpret_oem_data: bool = False
    output_sensor_state: bool = True
    output_sensor_thresholds: bool = False
    ignore_not_available_sensors: bool = False
    BMC_key: str | None = None


class _Params(BaseModel, frozen=True):
    agent: tuple[Literal["ipmitool"], _IPMIToolParams] | tuple[Literal["freeipmi"], _FreeIPMIParams]


def command_function(params: _Params, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    ipmi_command, options = params.agent
    yield SpecialAgentCommand(
        command_arguments=[
            host_config.primary_ip_config.address,
            options.username,
            options.password.unsafe(),
            ipmi_command,
            options.privilege_lvl,
            *(
                _ipmitool_args(options)
                if isinstance(options, _IPMIToolParams)
                else _freeipmi_args(options)
                if isinstance(options, _FreeIPMIParams)
                else ()
            ),
        ]
    )


def _ipmitool_args(options: _IPMIToolParams) -> Iterable[str]:
    if options.intf is None:
        return
    yield from ("--intf", options.intf)


def _freeipmi_args(options: _FreeIPMIParams) -> Iterable[str]:
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
        if (value := getattr(options, parameter)) is not None
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
        if getattr(options, checkbox)
    )


special_agent_ipmi_sensors = SpecialAgentConfig(
    name="ipmi_sensors",
    parameter_parser=_Params.model_validate,
    commands_function=command_function,
)
