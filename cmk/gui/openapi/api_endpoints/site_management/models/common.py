#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal, Self

from annotated_types import Ge, Interval
from pydantic import Discriminator, PlainSerializer, WithJsonSchema

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

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    HostAddressConverter,
    HostConverter,
    LDAPConnectionIDConverter,
    RelativeUrlConverter,
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.gui.watolib.hosts_and_folders import Host


@api_model
class IPSocketAttributes:
    port: Annotated[int, Interval(ge=1, le=65535)] = api_field(
        description="The TCP port to connect to.",
        example=6790,
    )
    encrypted: bool = api_field(
        description="To enable an encrypted connection.",
        example=True,
    )
    verify: bool | ApiOmitted = api_field(
        description="Verify server certificate.",
        example=True,
        default_factory=ApiOmitted,
    )


@api_model
class IP4Socket(IPSocketAttributes):
    socket_type: Literal["tcp"] = api_field(
        description="The tcp socket type",
        example="tcp",
    )
    host: Annotated[
        HostAddress,
        TypedPlainValidator(str, HostAddressConverter(allow_ipv6=False)),
        WithJsonSchema({"type": "string"}, mode="serialization"),
    ] = api_field(
        description="The IP4 address or domain name of the host.",
        example="127.0.0.1",
    )

    def to_internal(self) -> NetworkSocketInfo:
        return (
            "tcp",
            NetworkSocketDetails(
                address=(str(self.host), self.port),
                tls=(
                    "encrypted" if self.encrypted else "plain_text",
                    (
                        TLSParams(verify=self.verify)
                        if isinstance(self.verify, bool)
                        else TLSParams()
                    ),
                ),
            ),
        )


@api_model
class IP6Socket(IPSocketAttributes):
    socket_type: Literal["tcp6"] = api_field(
        description="The tcp6 socket type",
        example="tcp6",
    )
    host: Annotated[
        HostAddress,
        TypedPlainValidator(str, HostAddressConverter(allow_ipv4=False)),
        WithJsonSchema({"type": "string"}, mode="serialization"),
    ] = api_field(
        description="The IP6 address or domain name of the host.",
        example="5402:1db8:95a3:0000:0000:9a2e:0480:8334",
    )

    def to_internal(self) -> NetworkSocketInfo:
        return (
            "tcp6",
            NetworkSocketDetails(
                address=(str(self.host), self.port),
                tls=(
                    "encrypted" if self.encrypted else "plain_text",
                    (
                        TLSParams(verify=self.verify)
                        if isinstance(self.verify, bool)
                        else TLSParams()
                    ),
                ),
            ),
        )


@api_model
class UnixSocket:
    socket_type: Literal["unix"] = api_field(
        description="The unix socket type",
        example="unix",
    )
    path: str = api_field(
        description="When the connection name is unix, this is the path to the unix socket.",
        example="/path/to/your/unix_socket",
    )

    def to_internal(self) -> UnixSocketInfo:
        return ("unix", UnixSocketDetails(path=self.path))


@api_model
class LocalSocket:
    socket_type: Literal["local"] = api_field(
        description="The local socket type",
        example="local",
    )

    def to_internal(self) -> LocalSocketInfo:
        return ("local", None)


@api_model
class HeartbeatModel:
    interval: ApiOmitted | Annotated[int, Ge(1)] = api_field(
        description="The heartbeat interval for the TCP connection.",
        example=5,
        default_factory=ApiOmitted,
    )
    timeout: ApiOmitted | Annotated[float, Ge(0.1)] = api_field(
        description="The heartbeat timeout for the TCP connection.",
        example=2.0,
        default_factory=ApiOmitted,
    )


@api_model
class ProxyParamsModel:
    channels: ApiOmitted | Annotated[int, Interval(ge=2, le=50)] = api_field(
        description="The number of channels to keep open.",
        example=5,
        default_factory=ApiOmitted,
    )
    heartbeat: HeartbeatModel | ApiOmitted = api_field(
        description="The heartbeat interval and timeout configuration.",
        default_factory=ApiOmitted,
    )
    channel_timeout: ApiOmitted | Annotated[float, Ge(0.1)] = api_field(
        description="The timeout waiting for a free channel.",
        example=3.0,
        default_factory=ApiOmitted,
    )
    query_timeout: ApiOmitted | Annotated[float, Ge(0.1)] = api_field(
        description="The total query timeout.",
        example=120.0,
        default_factory=ApiOmitted,
    )
    connect_retry: ApiOmitted | Annotated[float, Ge(0.1)] = api_field(
        description="The cooling period after a failed connect/heartbeat.",
        example=4.0,
        default_factory=ApiOmitted,
    )
    cache: bool | ApiOmitted = api_field(
        description="Enable caching.",
        example=True,
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, params: ProxyConfigParams | None) -> Self | ApiOmitted:
        if params is None:
            return ApiOmitted()

        params_model = cls()

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

        return params_model


@api_model
class ProxyTcpModel:
    port: Annotated[int, Interval(ge=1, le=65535)] = api_field(
        description="The TCP port to connect to.",
        example=6790,
    )

    only_from: list[
        Annotated[
            HostAddress,
            TypedPlainValidator(str, HostAddressConverter()),
            WithJsonSchema({"type": "string"}, mode="serialization"),
        ],
    ] = api_field(
        description="Restrict access to these IP addresses.",
        example=["192.168.1.23"],
    )
    tls: bool | ApiOmitted = api_field(
        description="Encrypt TCP Livestatus connections.",
        example=False,
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, tcp: ProxyConfigTcp | None) -> Self | ApiOmitted:
        if tcp is not None and "port" in tcp:
            return cls(
                port=tcp["port"],
                only_from=[HostAddress(host) for host in tcp.get("only_from", [])],
                tls=tcp.get("tls", False),
            )
        return ApiOmitted()


@api_model
class Direct:
    use_livestatus_daemon: Literal["direct"] = api_field(
        description="Use livestatus daemon with direct connection.",
        example=True,
    )


@api_model
class UseProxy:
    use_livestatus_daemon: Literal["with_proxy"] = api_field(
        description="Use livestatus daemon with livestatus proxy.",
        example=True,
    )
    global_settings: bool = api_field(
        description="When use_livestatus_daemon is set to 'with_proxy', you can set this to True"
        " to use global setting or False to use custom parameters.",
        example=True,
    )
    tcp: ProxyTcpModel | ApiOmitted = api_field(
        description="Allow access via TCP configuration.",
        default_factory=ApiOmitted,
    )
    params: ProxyParamsModel | ApiOmitted = api_field(
        description="The live status proxy daemon parameters.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, proxy: ProxyConfig) -> Self:
        return cls(
            use_livestatus_daemon="with_proxy",
            global_settings=bool(proxy.get("params") is None),
            params=ProxyParamsModel.from_internal(proxy.get("params")),
            tcp=ProxyTcpModel.from_internal(proxy.get("tcp")),
        )

    def to_internal(self) -> ProxyConfig:
        proxyconfig = ProxyConfig()
        if isinstance(self.tcp, ProxyTcpModel):
            proxyconfig["tcp"] = ProxyConfigTcp(
                port=self.tcp.port,
                only_from=[str(ha) for ha in self.tcp.only_from],
            )
            if isinstance(self.tcp.tls, bool):
                proxyconfig["tcp"]["tls"] = self.tcp.tls

        if isinstance(self.params, ProxyParamsModel):
            params = ProxyConfigParams()
            if isinstance(self.params.channels, int):
                params["channels"] = self.params.channels

            if isinstance(self.params.heartbeat, HeartbeatModel):
                interval = self.params.heartbeat.interval
                timeout = self.params.heartbeat.timeout
                if isinstance(interval, int) and isinstance(timeout, float):
                    params["heartbeat"] = (interval, timeout)

            if isinstance(self.params.channel_timeout, float):
                params["channel_timeout"] = self.params.channel_timeout

            if isinstance(self.params.query_timeout, float):
                params["query_timeout"] = self.params.query_timeout

            if isinstance(self.params.connect_retry, float):
                params["connect_retry"] = self.params.connect_retry

            if isinstance(self.params.cache, bool):
                params["cache"] = self.params.cache

            proxyconfig["params"] = params

        if self.global_settings:
            proxyconfig["params"] = None

        return proxyconfig


@api_model
class StatusHostDisabled:
    status_host_set: Literal["disabled"] = api_field(
        description="disabled for 'no status host'",
        example="disabled",
    )


@api_model
class StatusHostEnabled:
    status_host_set: Literal["enabled"] = api_field(
        description="enabled for 'use the following status host'",
        example=False,
    )
    site: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
    ] = api_field(
        description="The site ID of the status host.",
        example="prod",
    )
    host: Annotated[
        Host,
        TypedPlainValidator(str, HostConverter(permission_type="monitor").host),
        PlainSerializer(lambda h: h.name(), return_type=str),
    ] = api_field(
        description="The host name of the status host.",
        example="host_1",
    )

    def to_internal(self) -> tuple[SiteId, str]:
        return self.site, self.host.name()


@api_model
class StatusConnectionModel:
    connection: Annotated[
        LocalSocket | IP4Socket | IP6Socket | UnixSocket, Discriminator("socket_type")
    ] = api_field(
        description="When connecting to remote site please make sure that Livestatus over TCP"
        " is activated there. You can use UNIX sockets to connect to foreign sites on localhost.",
    )
    proxy: Annotated[Direct | UseProxy, Discriminator("use_livestatus_daemon")] = api_field(
        description="The Livestatus proxy daemon configuration attributes.",
    )
    connect_timeout: int = api_field(
        description="The time that the GUI waits for a connection to the site to be established"
        " before the site is considered to be unreachable.",
        example=2,
    )
    persistent_connection: bool | ApiOmitted = api_field(
        description="If you enable persistent connections then Multisite will try to keep open"
        " the connection to the remote sites.",
        example=False,
        default_factory=ApiOmitted,
    )
    url_prefix: (
        ApiOmitted
        | Annotated[
            str,
            TypedPlainValidator(str, RelativeUrlConverter(must_endwith_one=["/"]).validate),
        ]
    ) = api_field(
        description="The URL prefix will be prepended to links of add-ons like NagVis when a link"
        " to such applications points to a host or service on that site.",
        example="/remote_1/",
        default_factory=ApiOmitted,
    )
    status_host: Annotated[
        StatusHostDisabled | StatusHostEnabled, Discriminator("status_host_set")
    ] = api_field(
        description="By specifying a status host for each non-local connection you prevent "
        "Multisite from running into timeouts when remote sites do not respond.",
    )
    disable_in_status_gui: bool | ApiOmitted = api_field(
        description="If you disable a connection, then no data of this site will be shown in the"
        " status GUI. The replication is not affected by this, however.",
        example=False,
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, status_connection: SiteConfiguration) -> Self:
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

        def _status_host_from_internal(
            status_host: tuple[SiteId, str] | None,
        ) -> StatusHostDisabled | StatusHostEnabled:
            if status_host is None:
                return StatusHostDisabled(status_host_set="disabled")

            host = Host.host(HostName(status_host[1]))
            assert host is not None
            return StatusHostEnabled(status_host_set="enabled", site=status_host[0], host=host)

        return cls(
            connection=_socket_from_internal(status_connection["socket"]),
            proxy=(
                Direct(use_livestatus_daemon="direct")
                if status_connection["proxy"] is None
                else UseProxy.from_internal(status_connection["proxy"])
            ),
            connect_timeout=status_connection["timeout"],
            persistent_connection=status_connection["persist"],
            url_prefix=status_connection["url_prefix"],
            status_host=_status_host_from_internal(status_connection["status_host"]),
            disable_in_status_gui=status_connection["disabled"],
        )


@api_model
class ConnectionWithoutReplicationModel:
    enable_replication: Literal[False] = api_field(
        description="Replication is disabled",
    )


@api_model
class UserSyncWithLdapModel:
    sync_with_ldap_connections: Literal["ldap"] = api_field(
        description="Sync with ldap connections.",
        example="ldap",
    )
    ldap_connections: list[
        Annotated[
            str,
            TypedPlainValidator(str, LDAPConnectionIDConverter.should_exist),
        ]
    ] = api_field(
        description="A list of existing ldap connections.",
        example=["LDAP_1", "LDAP_2"],
    )

    def to_internal(self) -> tuple[Literal["list"], list[str]]:
        return ("list", self.ldap_connections)


@api_model
class UserSyncAllModel:
    sync_with_ldap_connections: Literal["all"] = api_field(
        description="Sync with all connections.",
        example="all",
    )

    def to_internal(self) -> Literal["all"]:
        return "all"


@api_model
class UserSyncDisabledModel:
    sync_with_ldap_connections: Literal["disabled"] = api_field(
        description="Sync with disabled connections.",
        example="disabled",
    )

    def to_internal(self) -> None:
        return None


@api_model
class ConnectionModel:
    enable_replication: bool = api_field(
        description="Replication allows you to manage several monitoring sites with a logically"
        " centralized setup. Remote sites receive their configuration from the central sites.",
        example=True,
    )

    url_of_remote_site: (
        ApiOmitted
        | Annotated[
            str,
            TypedPlainValidator(
                str,
                RelativeUrlConverter(
                    allowed_to_be_empty=True,
                    must_startwith_one=["https", "http"],
                    must_endwith_one=["/check_mk/"],
                ).validate,
            ),
        ]
    ) = api_field(
        description="URL of the remote Checkmk including /check_mk/. This URL is in"
        " many cases the same as the URL-Prefix but with check_mk/ appended, but it must always"
        " be an absolute URL.",
        example="http://remote_site_1/check_mk/",
        default_factory=ApiOmitted,
    )
    disable_remote_configuration: bool = api_field(
        description="It is a good idea to disable access to Setup completely on the remote site."
        " Otherwise a user who does not now about the replication could make local changes that "
        "are overridden at the next configuration activation.",
        example=True,
    )
    ignore_tls_errors: bool = api_field(
        description="This might be needed to make the synchronization accept problems with SSL "
        "certificates when using an SSL secured connection.",
        example=False,
    )
    direct_login_to_web_gui_allowed: bool = api_field(
        description="When enabled, this site is marked for synchronisation every time a web GUI"
        " related option is changed and users are allowed to login to the web GUI of this site.",
        example=True,
    )
    user_sync: Annotated[
        UserSyncWithLdapModel | UserSyncAllModel | UserSyncDisabledModel,
        Discriminator("sync_with_ldap_connections"),
    ] = api_field(
        description="By default the users are synchronized automatically in the interval "
        "configured in the connection. For example the LDAP connector synchronizes the users"
        " every five minutes by default. The interval can be changed for each connection"
        " individually in the connection settings. Please note that the synchronization is only"
        " performed on the master site in distributed setups by default."
    )
    replicate_event_console: bool = api_field(
        description="This option enables the distribution of global settings and rules of the"
        " Event Console to the remote site. Any change in the local Event Console settings will"
        " mark the site as need sync. A synchronization will automatically reload the Event"
        "Console of the remote site.",
        example=True,
    )
    replicate_extensions: bool = api_field(
        description="If you enable the replication of MKPs then during each Activate Changes "
        "MKPs that are installed on your central site and all other files below the ~/local/ "
        "directory will be also transferred to the remote site. Note: all other MKPs and files"
        " below ~/local/ on the remote site will be removed.",
        example=True,
    )
    message_broker_port: int = api_field(
        description="The port used by the message broker to exchange messages.",
        example=5672,
    )
    is_trusted: bool = api_field(
        description="When this option is enabled the central site might get compromised by a rogue remote site. "
        "If you disable this option, some features, such as HTML rendering in service descriptions for the services monitored on this remote site, will no longer work. "
        "In case the sites are managed by different groups of people, especially when belonging to different organizations, we recommend to disable this setting.",
        example=False,
    )


@api_model
class SiteConnectionBaseModel:
    status_connection: StatusConnectionModel = api_field(
        description="The status connection attributes",
    )
    configuration_connection: ConnectionModel = api_field(
        description="The configuration connection attributes",
    )

    def base_to_internal(self) -> SiteConfiguration:
        # TODO: These three fields should have default values but currently blocked
        # by a pydantic limitation.
        persistent_connection = self.status_connection.persistent_connection
        disable_in_status_gui = self.status_connection.disable_in_status_gui
        url_prefix = self.status_connection.url_prefix

        site_configuration = SiteConfiguration(
            id=SiteId(""),
            alias="",
            status_host=None,
            socket=self.status_connection.connection.to_internal(),
            proxy=None,
            disabled=False
            if not isinstance(disable_in_status_gui, bool)
            else disable_in_status_gui,
            timeout=self.status_connection.connect_timeout,
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
            is_trusted=False,
        )

        if isinstance(self.status_connection.status_host, StatusHostEnabled):
            site_configuration["status_host"] = self.status_connection.status_host.to_internal()

        if isinstance(self.status_connection.proxy, UseProxy):
            site_configuration["proxy"] = self.status_connection.proxy.to_internal()

        site_configuration["replication"] = (
            "slave" if self.configuration_connection.enable_replication else None
        )

        if not isinstance(self.configuration_connection.url_of_remote_site, ApiOmitted):
            site_configuration["multisiteurl"] = self.configuration_connection.url_of_remote_site
        site_configuration["insecure"] = self.configuration_connection.ignore_tls_errors
        site_configuration["user_sync"] = self.configuration_connection.user_sync.to_internal()
        site_configuration["disable_wato"] = (
            self.configuration_connection.disable_remote_configuration
        )
        site_configuration["user_login"] = (
            self.configuration_connection.direct_login_to_web_gui_allowed
        )
        site_configuration["replicate_ec"] = self.configuration_connection.replicate_event_console
        site_configuration["replicate_mkps"] = self.configuration_connection.replicate_extensions
        site_configuration["message_broker_port"] = (
            self.configuration_connection.message_broker_port
        )
        site_configuration["is_trusted"] = self.configuration_connection.is_trusted

        return site_configuration
