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
    GraphApiConnectionParameters,
    Oauth2Parameters,
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

    if send_params.server:
        send_server = replace_macros(send_params.server, host_config.macros)
    else:
        send_server = host_config.primary_ip_config.address

    args.append(f"--send-server={send_server}")

    if (port := send_params.connection.port) is not None:
        args.append(f"--send-port={port}")

    match params.send:
        case ("SMTP", SMTPParameters() as smtp_params):
            if smtp_params.connection.tls:
                args.append("--send-tls")

            if auth := smtp_params.auth:
                args.extend(
                    [
                        "--send-username",
                        auth.username,
                        "--send-password-reference",
                        auth.password,
                    ]
                )
        case ("EWS", CommonParameters() as common_params):
            if not common_params.connection.disable_tls:
                args.append("--send-tls")

            if common_params.connection.disable_cert_validation:
                args.append("--send-disable-cert-validation")

            match common_params.auth:
                case ("basic", BasicAuthParameters() as ews_auth):
                    args += [
                        "--send-username",
                        ews_auth.username,
                        "--send-password-reference",
                        ews_auth.password,
                    ]
                case ("oauth2", Oauth2Parameters() as ews_auth):
                    args += [
                        "--send-client-id",
                        ews_auth.client_id,
                        "--send-client-secret-reference",
                        ews_auth.client_secret,
                        "--send-tenant-id",
                        ews_auth.tenant_id,
                    ]
                case _:
                    pass

            args.append(f"--send-email-address={common_params.email_address}")
        case ("GRAPHAPI", GraphApiConnectionParameters() as graph_params):
            oauth2 = graph_params.auth
            args += [
                "--fetch-initial-access-token-reference",
                oauth2.access_token,
                "--fetch-initial-refresh-token-reference",
                oauth2.refresh_token,
                "--fetch-authority",
                oauth2.authority,
                "--fetch-client-secret-reference",
                oauth2.client_secret,
                "--fetch-client-id",
                oauth2.client_id,
                "--fetch-tenant-id",
                oauth2.tenant_id,
            ]
        case (protocol, _):
            raise NotImplementedError(f"Sending mails is not implemented for {protocol}")
        case _:
            pass

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
