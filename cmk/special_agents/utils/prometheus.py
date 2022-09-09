#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Common functions used in Prometheus related Special agents
"""

from __future__ import annotations

from typing import Literal, TypedDict

from cmk.utils import password_store

from cmk.special_agents.utils.request_helper import create_api_connect_session, parse_api_url


class ConnectionSetting(TypedDict, total=False):
    url_address: str
    port: int
    path_prefix: str
    base_prefix: str


class ConnectionConfig(TypedDict):
    # The correct typing causes mypy to crash, but it would be:
    # class URLSetting(TypedDict):
    #     url_address: str
    #
    #
    # class HostSetting(TypedDict):
    #     port: int
    #     path_prefix: str
    #     base_prefix: str
    #
    #
    # URLConnection = tuple[Literal["url_custom"], URLSetting]
    # HostConnection = tuple[Literal["ip_address", "host_name"], HostSetting]
    # connection: URLConnection | HostConnection
    connection: tuple[Literal["url_custom", "ip_address", "host_name"], ConnectionSetting]
    host_address: str | None
    host_name: str | None


def _get_api_url(config: ConnectionConfig) -> str:
    type_, settings = config["connection"]
    if type_ == "ip_address":
        address = config["host_address"]
    elif type_ == "host_name":
        address = config["host_name"]
    elif type_ == "url_custom":
        address = settings["url_address"]

    port = settings.get("port")
    path_prefix = settings.get("path_prefix")
    base_prefix = settings.get("base_prefix")
    protocol = config.get("protocol")

    return parse_api_url(
        server_address=address,
        api_path="api/v1/",
        protocol=protocol,
        port=port,
        url_prefix=base_prefix,
        path_prefix=path_prefix,
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
