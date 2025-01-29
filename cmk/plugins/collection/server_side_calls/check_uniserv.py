#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig


class Address(BaseModel):
    street: str
    street_no: int
    city: str
    search_regex: str


class Parameters(BaseModel):
    port: int
    service: str
    check_version: bool
    check_address: tuple[Literal["no"], None] | tuple[Literal["yes"], Address]


def commands_check_uniserv(
    params: Parameters,
    host_config: HostConfig,
) -> Iterable[ActiveCheckCommand]:
    args: list[str] = [
        host_config.primary_ip_config.address,
        str(params.port),
        params.service,
    ]

    if params.check_version:
        yield ActiveCheckCommand(
            service_description=f"Uniserv {params.service} Version",
            command_arguments=(*args, "VERSION"),
        )

    if isinstance((addr := params.check_address[1]), Address):
        yield ActiveCheckCommand(
            service_description=f"Uniserv {params.service} Address {addr.city}",
            command_arguments=(
                *args,
                "ADDRESS",
                addr.street,
                str(addr.street_no),
                addr.city,
                addr.search_regex,
            ),
        )


active_check_uniserv = ActiveCheckConfig(
    name="uniserv",
    parameter_parser=Parameters.model_validate,
    commands_function=commands_check_uniserv,
)
