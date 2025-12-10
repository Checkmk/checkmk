#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.server_side_calls.internal import OAuth2Connection
from cmk.server_side_calls.v1 import HostConfig, replace_macros, Secret

from .options_models import BasicAuthParameters, FetchingParameters, Oauth2Parameters


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

    match fetch_params.auth:
        case OAuth2Connection() as oauth2:
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
        case tuple(("basic", BasicAuthParameters() as auth)):
            args += [
                "--fetch-username",
                auth.username,
                "--fetch-password-reference",
                auth.password,
            ]
        case tuple(("oauth2", Oauth2Parameters() as auth)):
            args += [
                f"--fetch-client-id={auth.client_id}",
                "--fetch-client-secret-reference",
                auth.client_secret,
                f"--fetch-tenant-id={auth.tenant_id}",
            ]
        case _:
            pass

    if fetch_params.email_address:
        args.append(f"--fetch-email-address={fetch_params.email_address}")

    return args


def timeout_to_args(timeout: float | None) -> Sequence[str]:
    if timeout is None:
        return []

    return [f"--connect-timeout={timeout:.0f}"]
