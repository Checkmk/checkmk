#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, replace_macros, Secret


class BasicAuth(BaseModel):
    auth: tuple[str, Secret]


class OAuth(BaseModel):
    auth: tuple[str, Secret, str]


class Connection(BaseModel):
    disable_tls: bool = False
    disable_cert_validation: bool = False
    port: int | None = None


class FetchParams(BaseModel):
    server: str | None = None
    connection: Connection
    auth: tuple[str, tuple[str, Secret]] | tuple[str, tuple[str, Secret, str]]
    email_address: str | None = None


class GeneralMailParams(BaseModel):
    fetch: tuple[str, FetchParams]
    connect_timeout: int | None = None


def get_host_address(server: str | None, host_config: HostConfig) -> str:
    if server is None:
        return host_config.primary_ip_config.address
    return replace_macros(server, host_config.macros)


def get_general_mail_arguments(
    params: GeneralMailParams, host_config: HostConfig
) -> list[str | Secret]:
    fetch_protocol, fetch_params = params.fetch
    connection_params = fetch_params.connection
    auth_type, auth_data = fetch_params.auth

    args: list[str | Secret] = [
        f"--fetch-protocol={fetch_protocol}",
        f"--fetch-server={get_host_address(fetch_params.server, host_config)}",
    ]

    # NOTE: this argument will be turned into `--fetch-disable-tls` when
    # refactoring all mailbox based active checks
    if not connection_params.disable_tls:
        args.append("--fetch-tls")

    if connection_params.disable_cert_validation:
        args.append("--fetch-disable-cert-validation")

    if connection_params.port is not None:
        args.append(f"--fetch-port={connection_params.port}")

    if auth_type == "basic":
        username, password = BasicAuth.model_validate({"auth": auth_data}).auth
        args += [
            f"--fetch-username={username}",
            password.with_format("--fetch-password=%s"),
        ]

    else:
        client_id, client_secret, tenant_id = OAuth.model_validate({"auth": auth_data}).auth
        args += [
            f"--fetch-client-id={client_id}",
            client_secret.with_format("--fetch-client-secret=%s"),
            f"--fetch-tenant-id={tenant_id}",
        ]

    if fetch_params.email_address is not None:
        args.append(f"--fetch-email-address={fetch_params.email_address}")

    if params.connect_timeout is not None:
        args.append(f"--connect-timeout={params.connect_timeout}")

    return args
