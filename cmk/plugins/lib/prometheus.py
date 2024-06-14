#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Common functions used in Prometheus related Special agents
"""

from typing import Required, TypedDict

from cmk.utils import password_store

from cmk.special_agents.v0_unstable.request_helper import (
    ApiSession,
    create_api_connect_session,
    parse_api_url,
)


class ConnectionConfig(TypedDict):
    connection: Required[str]
    protocol: Required[str]


def _get_api_url(config: ConnectionConfig) -> str:
    return parse_api_url(
        server_address=config["connection"],
        api_path="api/v1/",
        protocol="http" if config["protocol"] == "http" else "https",
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


def generate_api_session(connection_options: dict) -> ApiSession:
    return create_api_connect_session(
        connection_options["api_url"],
        auth=connection_options.get("auth"),
        token=connection_options.get("token"),
        no_cert_check=not connection_options["verify-cert"],
    )
