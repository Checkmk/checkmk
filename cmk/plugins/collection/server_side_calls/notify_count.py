#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
)


class NotifyCountParams(BaseModel):
    description: str
    interval: int
    num_per_contact: tuple[int, int] | None = None


def generate_notify_count_command(
    params: NotifyCountParams,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    args = ["-r", str(params.interval)]

    if params.num_per_contact is not None:
        warn, crit = params.num_per_contact
        args += ["-w", str(warn)]
        args += ["-c", str(crit)]

    description = replace_macros(params.description, host_config.macros)
    yield ActiveCheckCommand(service_description=f"Notify {description}", command_arguments=args)


active_check_notify_count = ActiveCheckConfig(
    name="notify_count",
    parameter_parser=NotifyCountParams.model_validate,
    commands_function=generate_notify_count_command,
)
