#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NotRequired, TypedDict


class BasicSettings(TypedDict):
    alias: str
    site_id: str
    customer: NotRequired[str]


class Connection(TypedDict, total=False):
    socket_type: Literal["tcp", "tcp6", "unix"]
    host: str
    port: int
    encrypted: bool
    verify: bool
    path: str


class ProxyHeartbeat(TypedDict, total=False):
    interval: int
    timeout: float


class ProxyParams(TypedDict, total=False):
    channels: int
    heartbeat: ProxyHeartbeat
    channel_timeout: float
    query_timeout: float
    connect_retry: float
    cache: bool


class ProxyTcp(TypedDict, total=False):
    port: int
    only_from: list[str]
    tls: bool


class Proxy(TypedDict, total=False):
    use_livestatus_daemon: Literal["with_proxy", "direct"]
    global_settings: bool
    params: ProxyParams
    tcp: ProxyTcp


class StatusHost(TypedDict, total=False):
    status_host_set: Literal["enabled", "disabled"]
    site: str
    host: str


class StatusConnectionRequired(TypedDict):
    connection: Connection
    proxy: Proxy
    connect_timeout: int
    persistent_connection: NotRequired[bool]
    url_prefix: NotRequired[str]
    status_host: StatusHost
    disable_in_status_gui: NotRequired[bool]


class ConfigurationConnection(TypedDict, total=False):
    enable_replication: bool
    url_of_remote_site: str
    disable_remote_configuration: bool
    ignore_tls_errors: bool
    direct_login_to_web_gui_allowed: bool
    user_sync: dict
    replicate_event_console: bool
    replicate_extensions: bool
    message_broker_port: int


class SiteConfig(TypedDict):
    basic_settings: BasicSettings
    status_connection: StatusConnectionRequired
    configuration_connection: ConfigurationConnection
    secret: NotRequired[str]


class APISiteConfig(TypedDict):
    site_config: SiteConfig
