#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pydantic import BaseModel

from cmk.plugins.emailchecks.forwarding_option import ForwardingOptions, SyslogForwarding
from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig

from .common import fetching_options_to_args, timeout_to_args
from .options_models import FetchingParameters


class Parameters(BaseModel):
    service_description: str
    fetch: FetchingParameters
    connect_timeout: float | None = None
    forward: ForwardingOptions | None = None


def check_mail_arguments(
    params: Parameters, host_config: HostConfig
) -> Iterable[ActiveCheckCommand]:
    yield ActiveCheckCommand(
        service_description=params.service_description,
        command_arguments=(
            *fetching_options_to_args(params.fetch, host_config),
            *timeout_to_args(params.connect_timeout),
            *(() if params.forward is None else _forwarding_options_to_args(params.forward)),
        ),
    )


def _forwarding_options_to_args(forward: ForwardingOptions) -> Iterable[str]:
    yield "--forward-ec"
    match forward.method:
        case "ec", ("spool" | "spool_local", str(value)):
            yield f"--forward-method=spool:{value}"
        case "ec", (_, str(value)):
            yield f"--forward-method={value}"
        case "syslog", SyslogForwarding() as sf:
            yield f"--forward-method={sf.protocol},{sf.address},{sf.port}"

    if forward.match_subject:
        yield f"--match-subject={forward.match_subject}"

    if forward.facility:
        yield f"--forward-facility={forward.facility[1]}"

    if forward.host:
        yield f"--forward-host={forward.host}"

    match forward.application:
        case "spec", configured_app:
            yield f"--forward-app={configured_app}"

    if forward.body_limit is not None:
        yield f"--body-limit={forward.body_limit}"

    if forward.cleanup:
        yield f"--cleanup={forward.cleanup[1]}"


active_check_mail = ActiveCheckConfig(
    name="mail",
    parameter_parser=Parameters.model_validate,
    commands_function=check_mail_arguments,
)
