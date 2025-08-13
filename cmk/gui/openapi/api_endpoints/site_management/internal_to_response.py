#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from livestatus import (
    LocalSocketInfo,
    NetworkSocketInfo,
    ProxyConfig,
    SiteConfiguration,
    UnixSocketInfo,
)

import cmk.ccc.version as cmk_version
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.gui.customer import customer_api
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.utils import paths

from .models.common import (
    ConnectionWithoutReplicationModel,
    ConnectionWithReplicationModel,
    Direct,
    HeartbeatModel,
    IP4Socket,
    IP6Socket,
    LocalSocket,
    ProxyParamsModel,
    ProxyTcpModel,
    StatusConnectionModel,
    StatusHostDisabled,
    StatusHostEnabled,
    UnixSocket,
    UseProxy,
    UserSyncAllModel,
    UserSyncDisabledModel,
    UserSyncWithLdapModel,
)
from .models.response_models import (
    BasicSettingsModel,
    SiteConnectionExtensionsModel,
    SiteConnectionModel,
)


def _socket_from_internal(
    socket: str | UnixSocketInfo | NetworkSocketInfo | LocalSocketInfo,
) -> LocalSocket | IP4Socket | IP6Socket | UnixSocket:
    if isinstance(socket, str):
        return LocalSocket(socket_type="local")

    if socket[0] == "unix":
        return UnixSocket(
            socket_type="unix",
            path=socket[1]["path"],
        )

    if socket[0] == "tcp":
        tls = socket[1]["tls"]
        ip4_socket = IP4Socket(
            socket_type="tcp",
            host=HostAddress(socket[1]["address"][0]),
            port=socket[1]["address"][1],
            encrypted=tls[0] == "encrypted",
        )

        if "verify" in tls[1]:
            ip4_socket.verify = tls[1]["verify"]

        return ip4_socket

    if socket[0] == "tcp6":
        tls = socket[1]["tls"]
        ip6_socket = IP6Socket(
            socket_type="tcp6",
            host=HostAddress(socket[1]["address"][0]),
            port=socket[1]["address"][1],
            encrypted=tls[0] == "encrypted",
        )
        if "verify" in tls[1]:
            ip6_socket.verify = tls[1]["verify"]

        return ip6_socket

    return LocalSocket(socket_type="local")


def _proxy_from_internal(proxy: ProxyConfig | None) -> Direct | UseProxy:
    if proxy is None:
        return Direct(use_livestatus_daemon="direct")

    use_proxy = UseProxy(
        use_livestatus_daemon="with_proxy",
        global_settings=bool(proxy.get("params") is None),
    )

    if (tcp_values := proxy.get("tcp")) and "port" in tcp_values:
        use_proxy.tcp = ProxyTcpModel(
            port=tcp_values["port"],
            only_from=[HostAddress(host) for host in tcp_values.get("only_from", [])],
            tls=tcp_values.get("tls", False),
        )

    if params := proxy.get("params"):
        params_model = ProxyParamsModel()

        if "channels" in params:
            params_model.channels = params["channels"]

        if "heartbeat" in params:
            params_model.heartbeat = HeartbeatModel(
                interval=params["heartbeat"][0],
                timeout=params["heartbeat"][1],
            )

        if "channel_timeout" in params:
            params_model.channel_timeout = params["channel_timeout"]

        if "query_timeout" in params:
            params_model.query_timeout = params["query_timeout"]

        if "connect_retry" in params:
            params_model.connect_retry = params["connect_retry"]

        if "cache" in params:
            params_model.cache = params["cache"]

        use_proxy.params = params_model

    return use_proxy


def _status_host_from_internal(
    status_host: tuple[SiteId, str] | None,
) -> StatusHostDisabled | StatusHostEnabled:
    if status_host is None:
        return StatusHostDisabled(status_host_set="disabled")

    host = Host.host(HostName(status_host[1]))
    assert host is not None

    return StatusHostEnabled(
        status_host_set="enabled",
        site=status_host[0],
        host=host,
    )


def _configuration_connection_from_internal(
    site_configuration: SiteConfiguration,
) -> ConnectionWithReplicationModel | ConnectionWithoutReplicationModel:
    if site_configuration.get("replication") is None:
        return ConnectionWithoutReplicationModel(enable_replication=False)

    def _user_sync_from_internal(
        user_sync: Literal["all"] | tuple[Literal["list"], list[str]] | None,
    ) -> UserSyncWithLdapModel | UserSyncAllModel | UserSyncDisabledModel:
        if user_sync == "all":
            return UserSyncAllModel(sync_with_ldap_connections="all")

        if isinstance(user_sync, tuple) and user_sync[0] == "list":
            return UserSyncWithLdapModel(
                sync_with_ldap_connections="ldap",
                ldap_connections=user_sync[1],
            )
        return UserSyncDisabledModel(sync_with_ldap_connections="disabled")

    return ConnectionWithReplicationModel(
        enable_replication=True,
        url_of_remote_site=site_configuration["multisiteurl"],
        disable_remote_configuration=site_configuration["disable_wato"],
        ignore_tls_errors=site_configuration["insecure"],
        direct_login_to_web_gui_allowed=site_configuration["user_login"],
        user_sync=_user_sync_from_internal(user_sync=site_configuration["user_sync"]),
        replicate_event_console=site_configuration["replicate_ec"],
        replicate_extensions=site_configuration["replicate_mkps"],
        message_broker_port=site_configuration["message_broker_port"],
    )


def from_internal(site_configuration: SiteConfiguration) -> SiteConnectionModel:
    """Converts a SiteConfiguration (internal spec) to a SiteConnectionModel (api response)."""

    site_connection_extensions = SiteConnectionExtensionsModel(
        basic_settings=BasicSettingsModel(
            site_id=site_configuration["id"],
            alias=site_configuration["alias"],
        ),
        status_connection=StatusConnectionModel(
            connection=_socket_from_internal(site_configuration["socket"]),
            proxy=_proxy_from_internal(site_configuration["proxy"]),
            connect_timeout=site_configuration["timeout"],
            persistent_connection=site_configuration["persist"],
            url_prefix=site_configuration["url_prefix"],
            status_host=_status_host_from_internal(site_configuration["status_host"]),
            disable_in_status_gui=site_configuration["disabled"],
        ),
        configuration_connection=_configuration_connection_from_internal(
            site_configuration=site_configuration
        ),
    )

    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME:
        site_connection_extensions.basic_settings.customer = site_configuration.get(
            "customer", customer_api().default_customer_id()
        )

    if secret := site_configuration.get("secret"):
        site_connection_extensions.secret = secret

    return SiteConnectionModel(
        domainType="site_connection",
        id=site_configuration["id"],
        title=site_configuration["alias"],
        extensions=site_connection_extensions,
        links=generate_links(
            domain_type="site_connection",
            identifier=site_configuration["id"],
            deletable=not (site_configuration["socket"] == ("local", None)),
        ),
    )
