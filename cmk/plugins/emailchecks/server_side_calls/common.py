#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.server_side_calls.v1 import HostConfig, replace_macros, Secret

from .options_models import BasicAuthParameters, FetchingParameters


def fetching_options_to_args(
    params: FetchingParameters,
    host_config: HostConfig,
) -> Sequence[str | Secret]:
    fetch_protocol, fetch_params = params
    fetch_server = (
        host_config.primary_ip_config.address
        if fetch_params.server is None
        else replace_macros(fetch_params.server, host_config.macros)
    )

    args: list[str | Secret] = [
        f"--fetch-protocol={fetch_protocol}",
        f"--fetch-server={fetch_server}",
    ]

    if not fetch_params.connection.disable_tls:
        args.append("--fetch-tls")

    if fetch_params.connection.disable_cert_validation:
        args.append("--fetch-disable-cert-validation")

    if (fetch_port := fetch_params.connection.port) is not None:
        args.append(f"--fetch-port={fetch_port}")

    if isinstance(auth := fetch_params.auth[1], BasicAuthParameters):
        args += [
            "--fetch-username",
            auth.username,
            "--fetch-password-reference",
            auth.password,
        ]

    else:
        args += [
            f"--fetch-client-id={auth.client_id}",
            "--fetch-client-secret-reference",
            auth.client_secret,
            f"--fetch-tenant-id={auth.tenant_id}",
        ]

    if fetch_params.email_address:
        args.append(f"--fetch-email-address={fetch_params.email_address}")

    return args


def timeout_to_args(timeout: float | None) -> Sequence[str]:
    if timeout is None:
        return []

    return [f"--connect-timeout={timeout:.0f}"]
