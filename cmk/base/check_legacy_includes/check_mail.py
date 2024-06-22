#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.base.check_api import passwordstore_get_cmdline


# Note: this is already migrated in cmk.plugins.emailchecks.server_side_calls.commons!
def general_check_mail_args_from_params(
    check_ident: str, params: dict[str, Any]
) -> list[str | tuple[str, str, str]]:
    try:
        fetch_protocol, fetch_params = params["fetch"]
        connection_params = fetch_params["connection"]
        auth_type, auth_data = fetch_params["auth"]
    except KeyError as exc:
        raise ValueError(
            f"Params for {check_ident} are faulty (missing {exc}), did you update the config?"
        )

    args: list[str | tuple[str, str, str]] = [
        f"--fetch-protocol={fetch_protocol}",
        f"--fetch-server={fetch_params.get('server', '$HOSTADDRESS$')}",
    ]

    # NOTE: this argument will be turned into `--fetch-disable-tls` when
    # refactoring all mailbox based active checks
    if not connection_params.get("disable_tls"):
        args.append("--fetch-tls")

    if connection_params.get("disable_cert_validation"):
        args.append("--fetch-disable-cert-validation")

    if (fetch_port := connection_params.get("port")) is not None:
        args.append(f"--fetch-port={fetch_port}")

    if auth_type == "basic":
        username, password = auth_data
        args += [
            f"--fetch-username={username}",
            passwordstore_get_cmdline("--fetch-password=%s", password),
        ]

    else:
        client_id, client_secret, tenant_id = auth_data
        args += [
            f"--fetch-client-id={client_id}",
            passwordstore_get_cmdline("--fetch-client-secret=%s", client_secret),
            f"--fetch-tenant-id={tenant_id}",
        ]

    if "email_address" in fetch_params:
        args.append(f"--fetch-email-address={fetch_params['email_address']}")

    if "connect_timeout" in params:
        args.append(f"--connect-timeout={params['connect_timeout']}")

    return args
