#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    replace_macros,
    Secret,
)

from .common import fetching_options_to_args, timeout_to_args
from .options_models import (
    BasicAuthParameters,
    CommonParameters,
    FetchingParameters,
    SendingParameters,
    SMTPParameters,
)


class Parameters(BaseModel):
    item: str
    subject: str | None = None
    send: SendingParameters
    fetch: FetchingParameters
    mail_from: str = ""
    mail_to: str = ""
    connect_timeout: float | None = None
    duration: tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]] = (
        "no_levels",
        None,
    )
    delete_messages: bool = False


def check_mail_loop_arguments(
    params: Parameters, host_config: HostConfig
) -> Iterable[ActiveCheckCommand]:
    args: list[str | Secret] = [
        *fetching_options_to_args(params.fetch, host_config),
        *timeout_to_args(params.connect_timeout),
    ]

    send_protocol, send_params = params.send

    args.append(f"--send-protocol={send_protocol}")
    send_server = (
        host_config.primary_ip_config.address
        if send_params.server is None
        else replace_macros(send_params.server, host_config.macros)
    )
    args.append(f"--send-server={send_server}")

    if (port := send_params.connection.port) is not None:
        args.append(f"--send-port={port}")

    if send_protocol == "SMTP":
        assert isinstance(send_params, SMTPParameters)
        if send_params.connection.tls:
            args.append("--send-tls")

        if auth := send_params.auth:
            args.extend(
                ["--send-username", auth.username, "--send-password-reference", auth.password]
            )

    elif send_protocol == "EWS":
        assert isinstance(send_params, CommonParameters)
        if not send_params.connection.disable_tls:
            args.append("--send-tls")

        if send_params.connection.disable_cert_validation:
            args.append("--send-disable-cert-validation")

        _auth_type, ews_auth = send_params.auth
        if isinstance(ews_auth, BasicAuthParameters):
            args += [
                "--send-username",
                ews_auth.username,
                "--send-password-reference",
                ews_auth.password,
            ]
        else:
            args += [
                "--send-client-id",
                ews_auth.client_id,
                "--send-client-secret-reference",
                ews_auth.client_secret,
                "--send-tenant-id",
                ews_auth.tenant_id,
            ]

        args.append(f"--send-email-address={send_params.email_address}")
    else:
        raise NotImplementedError(f"Sending mails is not implemented for {send_protocol}")

    args.append(f"--mail-from={params.mail_from}")
    args.append(f"--mail-to={params.mail_to}")

    if params.delete_messages:
        args.append("--delete-messages")

    args.append(f"--status-suffix={host_config.name}-{params.item}")

    _levels_type, levels = params.duration
    if levels is not None:
        args.append(f"--warning={levels[0]:.0f}")
        args.append(f"--critical={levels[1]:.0f}")

    if params.subject is not None:
        args.append(f"--subject={params.subject}")

    yield ActiveCheckCommand(
        service_description=f"Mail Loop {params.item}",
        command_arguments=args,
    )


active_check_mail_loop = ActiveCheckConfig(
    name="mail_loop",
    parameter_parser=Parameters.model_validate,
    commands_function=check_mail_loop_arguments,
)
