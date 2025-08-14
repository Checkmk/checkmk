#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from livestatus import (
    LocalSocketInfo,
    NetworkSocketDetails,
    NetworkSocketInfo,
    ProxyConfig,
    ProxyConfigParams,
    ProxyConfigTcp,
    SiteConfiguration,
    TLSParams,
    UnixSocketDetails,
    UnixSocketInfo,
)

from .models.common import (
    ConnectionWithReplicationModel,
    HeartbeatModel,
    IP4Socket,
    IP6Socket,
    LocalSocket,
    ProxyParamsModel,
    ProxyTcpModel,
    StatusConnectionModel,
    StatusHostEnabled,
    UnixSocket,
    UseProxy,
    UserSyncAllModel,
    UserSyncWithLdapModel,
)
from .models.request_models import SiteConnectionCreate


def _socket_to_internal(
    socket_type: LocalSocket | IP4Socket | IP6Socket | UnixSocket,
) -> UnixSocketInfo | NetworkSocketInfo | LocalSocketInfo:
    if isinstance(socket_type, LocalSocket):
        return ("local", None)

    if isinstance(socket_type, IP4Socket):
        return (
            "tcp",
            NetworkSocketDetails(
                address=(
                    str(socket_type.host),
                    socket_type.port,
                ),
                tls=(
                    "encrypted" if socket_type.encrypted else "plain_text",
                    (
                        TLSParams(verify=socket_type.verify)
                        if isinstance(socket_type.verify, bool)
                        else TLSParams()
                    ),
                ),
            ),
        )
    if isinstance(socket_type, IP6Socket):
        return (
            "tcp6",
            NetworkSocketDetails(
                address=(
                    str(socket_type.host),
                    socket_type.port,
                ),
                tls=(
                    "encrypted" if socket_type.encrypted else "plain_text",
                    (
                        TLSParams(verify=socket_type.verify)
                        if isinstance(socket_type.verify, bool)
                        else TLSParams()
                    ),
                ),
            ),
        )

    return ("unix", UnixSocketDetails(path=socket_type.path))


def _status_connection_to_internal(
    status_connection: StatusConnectionModel,
    site_configuration: SiteConfiguration,
) -> None:
    if isinstance(status_connection.status_host, StatusHostEnabled):
        site_configuration["status_host"] = (
            status_connection.status_host.site,
            status_connection.status_host.host.name(),
        )
    if isinstance(status_connection.proxy, UseProxy):
        proxyconfig = ProxyConfig()
        if isinstance(status_connection.proxy.tcp, ProxyTcpModel):
            proxyconfig["tcp"] = ProxyConfigTcp(
                port=status_connection.proxy.tcp.port,
                only_from=[str(ha) for ha in status_connection.proxy.tcp.only_from],
            )
            if isinstance(status_connection.proxy.tcp.tls, bool):
                proxyconfig["tcp"]["tls"] = status_connection.proxy.tcp.tls

        if isinstance(status_connection.proxy.params, ProxyParamsModel):
            params = ProxyConfigParams()
            if isinstance(status_connection.proxy.params.channels, int):
                params["channels"] = status_connection.proxy.params.channels

            if isinstance(status_connection.proxy.params.heartbeat, HeartbeatModel):
                interval = status_connection.proxy.params.heartbeat.interval
                timeout = status_connection.proxy.params.heartbeat.timeout
                if isinstance(interval, int) and isinstance(timeout, float):
                    params["heartbeat"] = (interval, timeout)

            if isinstance(status_connection.proxy.params.channel_timeout, float):
                params["channel_timeout"] = status_connection.proxy.params.channel_timeout

            if isinstance(status_connection.proxy.params.query_timeout, float):
                params["query_timeout"] = status_connection.proxy.params.query_timeout

            if isinstance(status_connection.proxy.params.connect_retry, float):
                params["connect_retry"] = status_connection.proxy.params.connect_retry

            if isinstance(status_connection.proxy.params.cache, bool):
                params["cache"] = status_connection.proxy.params.cache

            proxyconfig["params"] = params

        # This is weird.  You can set the params above but also set the params to
        # None with global_settings = True
        if status_connection.proxy.global_settings:
            proxyconfig["params"] = None

        site_configuration["proxy"] = proxyconfig


def _configuration_connection_to_internal(
    configuration_connection: ConnectionWithReplicationModel,
    site_configuration: SiteConfiguration,
) -> None:
    site_configuration["replication"] = "slave"
    site_configuration["multisiteurl"] = configuration_connection.url_of_remote_site
    site_configuration["disable_wato"] = configuration_connection.disable_remote_configuration

    site_configuration["insecure"] = configuration_connection.ignore_tls_errors
    site_configuration["user_login"] = configuration_connection.direct_login_to_web_gui_allowed

    if isinstance(configuration_connection.user_sync, UserSyncAllModel):
        site_configuration["user_sync"] = "all"

    if isinstance(configuration_connection.user_sync, UserSyncWithLdapModel):
        site_configuration["user_sync"] = (
            "list",
            configuration_connection.user_sync.ldap_connections,
        )

    site_configuration["replicate_ec"] = configuration_connection.replicate_event_console
    site_configuration["replicate_mkps"] = configuration_connection.replicate_extensions

    # This is part of the ConnectionWithReplicationModel but should be independent
    # In the UI you can set the broker port when replication is disabled.
    site_configuration["message_broker_port"] = configuration_connection.message_broker_port


def to_internal(incoming: SiteConnectionCreate) -> SiteConfiguration:
    # TODO: These three fields should have default values but currently blocked
    # by a pydantic limitation.
    persistent_connection = incoming.status_connection.persistent_connection
    disable_in_status_gui = incoming.status_connection.disable_in_status_gui
    url_prefix = incoming.status_connection.url_prefix

    site_configuration = SiteConfiguration(
        id=incoming.basic_settings.site_id,
        alias=incoming.basic_settings.alias,
        status_host=None,
        socket=_socket_to_internal(incoming.status_connection.connection),
        proxy=None,
        disabled=False if not isinstance(disable_in_status_gui, bool) else disable_in_status_gui,
        timeout=incoming.status_connection.connect_timeout,
        persist=False if not isinstance(persistent_connection, bool) else persistent_connection,
        url_prefix="" if not isinstance(url_prefix, str) else url_prefix,
        replication=None,
        multisiteurl="",
        disable_wato=True,
        insecure=False,
        user_login=True,
        user_sync=None,
        replicate_ec=True,
        replicate_mkps=True,
        message_broker_port=5672,
    )

    if isinstance(incoming.secret, str):
        site_configuration["secret"] = incoming.secret

    if isinstance(incoming.basic_settings.customer, str):
        site_configuration["customer"] = incoming.basic_settings.customer

    _status_connection_to_internal(
        status_connection=incoming.status_connection,
        site_configuration=site_configuration,
    )

    if isinstance(incoming.configuration_connection, ConnectionWithReplicationModel):
        _configuration_connection_to_internal(
            configuration_connection=incoming.configuration_connection,
            site_configuration=site_configuration,
        )

    return site_configuration
