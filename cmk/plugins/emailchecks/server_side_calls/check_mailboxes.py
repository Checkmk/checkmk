#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.plugins.emailchecks.server_side_calls.common import (
    fetching_options_to_args,
    timeout_to_args,
)
from cmk.plugins.emailchecks.server_side_calls.options_models import FetchingParameters
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig, Secret

_SimpleFloatLevels = (
    tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]]
)
_SimpleIntLevels = tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[int, int]]


class Parameters(BaseModel):
    service_description: str
    fetch: FetchingParameters
    connect_timeout: float | None = None
    age: _SimpleFloatLevels = ("no_levels", None)
    age_newest: _SimpleFloatLevels = ("no_levels", None)
    count: _SimpleIntLevels = ("no_levels", None)
    mailboxes: Sequence[str] = ()


def check_mailboxes_arguments(
    params: Parameters, host_config: HostConfig
) -> Iterable[ActiveCheckCommand]:
    args: list[str | Secret] = [
        *fetching_options_to_args(params.fetch, host_config),
        *timeout_to_args(params.connect_timeout),
    ]

    match params.age:
        case ("fixed", (warn, crit)):
            args += [f"--warn-age-oldest={warn:.0f}", f"--crit-age-oldest={crit:.0f}"]

    match params.age_newest:
        case ("fixed", (warn, crit)):
            args += [f"--warn-age-newest={warn:.0f}", f"--crit-age-newest={crit:.0f}"]

    match params.count:
        case ("fixed", (warn, crit)):
            args += [f"--warn-count={warn}", f"--crit-count={crit}"]

    args += [f"--mailbox={mb}" for mb in params.mailboxes]

    yield ActiveCheckCommand(
        service_description=params.service_description,
        command_arguments=args,
    )


active_check_mailboxes = ActiveCheckConfig(
    name="mailboxes",
    parameter_parser=Parameters.model_validate,
    commands_function=check_mailboxes_arguments,
)
