#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import host_name, passwordstore_get_cmdline
from cmk.base.check_legacy_includes.check_mail import general_check_mail_args_from_params
from cmk.base.config import active_check_info

CHECK_IDENT = "check_mail_loop"


def check_mail_loop_arguments(params):  # pylint: disable=too-many-branches
    args: list[str | tuple[str, str, str]] = general_check_mail_args_from_params(
        CHECK_IDENT, params
    )

    try:
        send_protocol, send_params = params["send"]
        connection_params = send_params["connection"]
    except KeyError as exc:
        raise ValueError(
            f"{params['item']} --- Params for check_mail_loop are faulty (missing {exc}), did you update the config?"
        )

    args.append(f"--send-protocol={send_protocol}")
    args.append(f"--send-server={send_params.get('server', '$HOSTADDRESS$')}")
    if (port := connection_params.get("port")) is not None:
        args.append(f"--send-port={port}")

    if send_protocol == "SMTP":
        if connection_params.get("tls"):
            args.append("--send-tls")

        if auth_params := send_params.get("auth"):
            username, password = auth_params
            args.append(f"--send-username={username}")
            args.append(passwordstore_get_cmdline("--send-password=%s", password))
    elif send_protocol == "EWS":
        if not connection_params.get("disable_tls"):
            args.append("--send-tls")

        if connection_params.get("disable_cert_validation"):
            args.append("--send-disable-cert-validation")

        auth_type, auth_data = send_params.get("auth")
        if auth_type == "basic":
            username, password = auth_data
            args += [
                f"--send-username={username}",
                passwordstore_get_cmdline("--send-password=%s", password),
            ]
        else:
            client_id, client_secret, tenant_id = auth_data
            args += [
                f"--send-client-id={client_id}",
                passwordstore_get_cmdline("--send-client-secret=%s", client_secret),
                f"--send-tenant-id={tenant_id}",
            ]

        args.append(f"--send-email-address={send_params.get('email_address')}")
    else:
        raise NotImplementedError(f"Sending mails is not implemented for {send_protocol}")

    args.append(f"--mail-from={params['mail_from']}")
    args.append(f"--mail-to={params['mail_to']}")

    if "delete_messages" in params:
        args.append("--delete-messages")

    args.append(f"--status-suffix={host_name()}-{params['item']}")

    if "duration" in params:
        warning, critical = params["duration"]
        args.append(f"--warning={warning}")
        args.append(f"--critical={critical}")

    if "subject" in params:
        args.append(f"--subject={params['subject']}")

    return args


active_check_info["mail_loop"] = {
    "command_line": f"{CHECK_IDENT} $ARG1$",
    "argument_function": check_mail_loop_arguments,
    "service_description": lambda params: f"Mail Loop {params['item']}",
}
