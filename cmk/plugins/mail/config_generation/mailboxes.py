#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    Secret,
)

from .utils import GeneralMailParams, get_general_mail_arguments


class MailboxesParams(GeneralMailParams):
    service_description: str
    retrieve_max: int | None = None
    age: tuple[int, int] | None = None
    age_newest: tuple[int, int] | None = None
    count: tuple[int, int] | None = None
    mailboxes: Sequence[str] = []


def generate_mailboxes_command(
    params: MailboxesParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = get_general_mail_arguments(params, host_config)

    if params.retrieve_max is not None:
        args.append(f"--retrieve-max={params.retrieve_max}")

    if params.age is not None:
        warn, crit = params.age
        args += [f"--warn-age-oldest={warn}", f"--crit-age-oldest={crit}"]

    if params.age_newest is not None:
        warn, crit = params.age_newest
        args += [f"--warn-age-newest={warn}", f"--crit-age-newest={crit}"]

    if params.count is not None:
        warn, crit = params.count
        args += [f"--warn-count={warn}", f"--crit-count={crit}"]

    for mb in params.mailboxes:
        args.append(f"--mailbox={mb}")

    yield ActiveCheckCommand(service_description=params.service_description, command_arguments=args)


active_check_mailboxes = ActiveCheckConfig(
    name="mailboxes",
    parameter_parser=MailboxesParams.model_validate,
    commands_function=generate_mailboxes_command,
)
