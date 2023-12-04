#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import get_secret_from_params, HostConfig, Secret

SecretType = Literal["store", "password"]


class BasicAuth(BaseModel):
    auth: tuple[str, tuple[SecretType, str]]


class OAuth(BaseModel):
    auth: tuple[str, tuple[SecretType, str], str]


class Connection(BaseModel):
    disable_tls: bool = False
    disable_cert_validation: bool = False
    port: int | None = None


class FetchParams(BaseModel):
    server: str | None = None
    connection: Connection
    auth: tuple[str, tuple[str, tuple[str, str]]] | tuple[str, tuple[str, tuple[str, str], str]]
    email_address: str | None = None


class GeneralMailParams(BaseModel):
    fetch: tuple[str, FetchParams]
    connect_timeout: int | None = None


def get_host_address(server: str | None, host_config: HostConfig) -> str:
    if server is None or server == "$HOSTADDRESS$":
        if host_config.address:
            return host_config.address
        raise ValueError("No IP address available")

    if server == "$HOSTNAME$":
        return host_config.name

    return server


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
        secret_type, secret_value = password
        args += [
            f"--fetch-username={username}",
            get_secret_from_params(secret_type, secret_value, display_format="--fetch-password=%s"),
        ]

    else:
        client_id, client_secret, tenant_id = OAuth.model_validate({"auth": auth_data}).auth
        client_secret_type, client_secret_value = client_secret
        args += [
            f"--fetch-client-id={client_id}",
            get_secret_from_params(
                client_secret_type, client_secret_value, "--fetch-client-secret=%s"
            ),
            f"--fetch-tenant-id={tenant_id}",
        ]

    if fetch_params.email_address is not None:
        args.append(f"--fetch-email-address={fetch_params.email_address}")

    if params.connect_timeout is not None:
        args.append(f"--connect-timeout={params.connect_timeout}")

    return args
