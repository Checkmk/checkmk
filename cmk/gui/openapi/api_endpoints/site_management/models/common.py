#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import Ge, Interval
from pydantic import Discriminator, PlainSerializer, WithJsonSchema

from cmk.ccc.hostaddress import HostAddress
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


@api_model
class LocalSocket:
    socket_type: Literal["local"] = api_field(
        description="The local socket type",
        example="local",
    )


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
        description="The URL prefix will be prepended to links of addons like NagVis when a link"
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


@api_model
class UserSyncAllModel:
    sync_with_ldap_connections: Literal["all"] = api_field(
        description="Sync with all connections.",
        example="all",
    )


@api_model
class UserSyncDisabledModel:
    sync_with_ldap_connections: Literal["disabled"] = api_field(
        description="Sync with disabled connections.",
        example="disabled",
    )


@api_model
class ConnectionWithReplicationModel:
    enable_replication: Literal[True] = api_field(
        description="Replication allows you to manage several monitoring sites with a logically"
        " centralized setup. Remote sites receive their configuration from the central sites.",
    )
    url_of_remote_site: Annotated[
        str,
        TypedPlainValidator(
            str,
            RelativeUrlConverter(
                must_startwith_one=["https", "http"],
                must_endwith_one=["/check_mk/"],
            ).validate,
        ),
    ] = api_field(
        default="",
        description="URL of the remote Checkmk including /check_mk/. This URL is in"
        " many cases the same as the URL-Prefix but with check_mk/ appended, but it must always"
        " be an absolute URL.",
        example="http://remote_site_1/check_mk/",
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


@api_model
class SiteConnectionBaseModel:
    status_connection: StatusConnectionModel = api_field(
        description="The status connection attributes",
    )
    configuration_connection: Annotated[
        ConnectionWithReplicationModel | ConnectionWithoutReplicationModel,
        Discriminator("enable_replication"),
    ] = api_field(
        description="The configuration connection attributes",
    )
    secret: str | ApiOmitted = api_field(
        description="The shared secret used by the central site to authenticate with "
        "the remote site for configuring Checkmk.",
        example="secret",
        default_factory=ApiOmitted,
    )
