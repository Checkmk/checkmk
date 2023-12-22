#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    parse_secret,
    Secret,
)

from .utils import BasicAuth, GeneralMailParams, get_general_mail_arguments, get_host_address, OAuth


class ConnectionParams(BaseModel):
    disable_tls: bool = False
    disable_cert_validation: bool = False
    port: int | None = None
    tls: bool = False


class SendParams(BaseModel):
    server: str | None = None
    connection: ConnectionParams
    auth: tuple[str, tuple[str, str]] | tuple[str, tuple[str, tuple[str, str]]] | tuple[
        str, tuple[str, tuple[str, str], str]
    ] | None = None
    email_address: str | None = None


class MailLoopParams(GeneralMailParams):
    item: str
    subject: str | None = None
    send: tuple[str, SendParams]
    mail_from: str
    mail_to: str
    delete_messages: bool = False
    duration: tuple[int, int] | None = None


def generate_mail_loop_command(  # pylint: disable=too-many-branches
    params: MailLoopParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    args: list[str | Secret] = get_general_mail_arguments(params, host_config)

    send_protocol, send_params = params.send
    connection_params = send_params.connection

    args.append(f"--send-protocol={send_protocol}")
    args.append(f"--send-server={get_host_address(send_params.server, host_config)}")
    if connection_params.port is not None:
        args.append(f"--send-port={connection_params.port}")

    if send_protocol == "SMTP":
        if connection_params.tls:
            args.append("--send-tls")

        if send_params.auth is not None:
            username, password = BasicAuth.model_validate({"auth": send_params.auth}).auth
            args.append(f"--send-username={username}")
            args.append(parse_secret(password, display_format="--send-password=%s"))
    elif send_protocol == "EWS":
        if not connection_params.disable_tls:
            args.append("--send-tls")

        if connection_params.disable_cert_validation:
            args.append("--send-disable-cert-validation")

        if not isinstance(send_params.auth, tuple):
            raise TypeError("Invalid auth parameter")

        auth_type, auth_data = send_params.auth
        if auth_type == "basic":
            username, password = BasicAuth.model_validate({"auth": auth_data}).auth
            args += [
                f"--send-username={username}",
                parse_secret(password, display_format="--send-password=%s"),
            ]
        else:
            client_id, client_secret, tenant_id = OAuth.model_validate({"auth": auth_data}).auth
            args += [
                f"--send-client-id={client_id}",
                parse_secret(
                    client_secret,
                    display_format="--send-client-secret=%s",
                ),
                f"--send-tenant-id={tenant_id}",
            ]

        args.append(f"--send-email-address={send_params.email_address}")
    else:
        raise NotImplementedError(f"Sending mails is not implemented for {send_protocol}")

    args.append(f"--mail-from={params.mail_from}")
    args.append(f"--mail-to={params.mail_to}")

    if params.delete_messages:
        args.append("--delete-messages")

    args.append(f"--status-suffix={host_config.name}-{params.item}")

    if params.duration is not None:
        warning, critical = params.duration
        args.append(f"--warning={warning}")
        args.append(f"--critical={critical}")

    if params.subject is not None:
        args.append(f"--subject={params.subject}")

    yield ActiveCheckCommand(service_description=f"Mail Loop {params.item}", command_arguments=args)


active_check_mail_loop = ActiveCheckConfig(
    name="mail_loop",
    parameter_parser=MailLoopParams.model_validate,
    commands_function=generate_mail_loop_command,
)
