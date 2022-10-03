#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Common functions used in Prometheus related Special agents
"""

from typing import Literal, TypedDict

from cmk.utils import password_store

from cmk.special_agents.utils.request_helper import create_api_connect_session, parse_api_url

ConnectionSetting = TypedDict(
    "ConnectionSetting",
    {
        "url_address": str,
        "port": int | None,
        "path-prefix": str | None,
    },
    total=False,
)


class ConnectionConfig(TypedDict):
    # This would be the correct typing:
    # URLSetting = TypedDict(
    #     "URLSetting",
    #     {
    #         "url_address": str,
    #     },
    # )

    # HostSetting = TypedDict(
    #     "HostSetting",
    #     {
    #         "port": int | None,
    #         "path-prefix": str | None,
    #     },
    # )

    # URLConnection = tuple[Literal["url_custom"], URLSetting]
    # HostConnection = tuple[Literal["ip_address", "host_name"], HostSetting]
    # connection: URLConnection | HostConnection
    # However, it causes mypy to crash.

    connection: tuple[Literal["url_custom", "ip_address", "host_name"], ConnectionSetting]
    host_address: str | None
    host_name: str | None


def _get_api_url(config: ConnectionConfig) -> str:
    match config["connection"]:
        case "url_custom", settings:
            address = settings["url_address"]
        case "ip_address", settings:
            address = config["host_address"]
        case "host_name", settings:
            address = config["host_name"]

    port = settings.get("port")
    url_prefix = settings.get("path-prefix")
    protocol = config.get("protocol")

    return parse_api_url(
        server_address=address,
        api_path="api/v1/",
        protocol=protocol,
        port=port,
        url_prefix=url_prefix,
    )


def extract_connection_args(config):
    connection_args = {
        "verify-cert": config.get("verify-cert", False),
    }

    if "auth_basic" in config:
        auth_info = config["auth_basic"][1]
        if config["auth_basic"][0] == "auth_login":
            connection_args.update(
                {
                    "auth": (
                        auth_info["username"],
                        password_store.extract(auth_info["password"]),
                    )
                }
            )
        else:
            connection_args.update({"token": password_store.extract(auth_info["token"])})

    connection_args["api_url"] = _get_api_url(config)
    return connection_args


def generate_api_session(connection_options):
    return create_api_connect_session(
        connection_options["api_url"],
        auth=connection_options.get("auth"),
        token=connection_options.get("token"),
        no_cert_check=not connection_options["verify-cert"],
    )
