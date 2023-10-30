#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from pydantic import BaseModel

from cmk.config_generation.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    Secret,
)

from .utils import GeneralMailParams, get_general_mail_arguments


class ForwardParams(BaseModel):
    method: str | None = None
    match_subject: str | None = None
    facility: int | None = None
    host: str | None = None
    application: str | None = None
    body_limit: int | None = None
    cleanup: bool | str | None = None


class MailParams(GeneralMailParams):
    service_description: str
    forward: ForwardParams | None = None


def generate_mail_command(
    params: MailParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    description = params.service_description
    args: list[str | Secret] = get_general_mail_arguments(params, host_config)

    if params.forward is None:
        yield ActiveCheckCommand(service_description=description, command_arguments=args)
        return

    args.append("--forward-ec")

    if params.forward.method is not None:
        args.append(f"--forward-method={params.forward.method}")

    if params.forward.match_subject is not None:
        args.append(f"--match-subject={params.forward.match_subject}")

    # int - can be 0
    if params.forward.facility is not None:
        args.append(f"--forward-facility={params.forward.facility}")

    if params.forward.host is not None:
        args.append(f"--forward-host={params.forward.host}")

    if params.forward.application is not None:
        args.append(f"--forward-app={params.forward.application}")

    # int - can be 0
    if params.forward.body_limit is not None:
        args.append(f"--body-limit={params.forward.body_limit}")

    if isinstance(params.forward.cleanup, bool):  # can never be False
        args.append("--cleanup=delete")

    elif isinstance(params.forward.cleanup, str):
        args.append(f"--cleanup={params.forward.cleanup}")

    yield ActiveCheckCommand(service_description=description, command_arguments=args)


active_check_mail = ActiveCheckConfig(
    name="mail", parameter_parser=MailParams.model_validate, commands_function=generate_mail_command
)
