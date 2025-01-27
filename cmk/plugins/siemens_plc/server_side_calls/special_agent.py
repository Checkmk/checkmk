#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class _ValueParams(BaseModel, frozen=True):
    area: tuple[str, int | None]
    address: float
    data_type: tuple[str, int | None]
    value_type: str
    id: str


class _DeviceParams(BaseModel, frozen=True):
    host_name: str
    host_address: str
    rack: int
    slot: int
    tcp_port: int
    values: Sequence[_ValueParams]


class _Params(BaseModel, frozen=True):
    devices: Sequence[_DeviceParams]
    values: Sequence[_ValueParams]
    timeout: int | None = None


def _commands_function(
    params: _Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args = []
    if params.timeout is not None:
        args += ["--timeout", str(params.timeout)]
    for device in params.devices:
        args += ["--hostspec", _serialize_device(device, params.values)]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_siemens_plc = SpecialAgentConfig(
    name="siemens_plc",
    parameter_parser=_Params.model_validate,
    commands_function=_commands_function,
)


def _serialize_device(
    device: _DeviceParams,
    global_values: Sequence[_ValueParams],
) -> str:
    return (
        f"{device.host_name};{device.host_address};{device.rack};{device.slot};{device.tcp_port}"
    ) + (
        ";" + ";".join(_serialize_value(value) for value in values)
        if (values := [*global_values, *device.values])
        else ""
    )


def _serialize_value(value: _ValueParams) -> str:
    return (
        f"{_serialize_tuple_value_field(value.area)},"
        f"{value.address},"
        f"{_serialize_tuple_value_field(value.data_type)},"
        f"{'None' if value.value_type == 'unclassified' else value.value_type},"
        f"{value.id}"
    )


def _serialize_tuple_value_field(field: tuple[str, int | None]) -> str:
    return field[0] if field[1] is None else f"{field[0]}:{field[1]}"
