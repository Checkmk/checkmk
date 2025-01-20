#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.site_management.common import default_config_example
from cmk.gui.openapi.restful_objects.response_schemas import (
    DomainObject,
    DomainObjectCollection,
)

from cmk import fields


class HeartbeatOutput(BaseSchema):
    interval = fields.Integer(
        required=False,
        description="The heartbeat interval for the TCP connection.",
        example=5,
    )
    timeout = gui_fields.Timeout(
        minimum=0.1,
        required=False,
        description="The heartbeat timeout for the TCP connection.",
        example=2.0,
    )


class ProxyParamsOutput(BaseSchema):
    channels = fields.Integer(
        required=False,
        description="The number of channels to keep open.",
        example=5,
    )
    heartbeat = fields.Nested(
        HeartbeatOutput,
        required=False,
        description="The heartbeat interval and timeout configuration.",
    )
    channel_timeout = gui_fields.Timeout(
        minimum=0.1,
        required=False,
        description="The timeout waiting for a free channel.",
        example=3.0,
    )
    query_timeout = gui_fields.Timeout(
        minimum=0.1,
        required=False,
        description="The total query timeout.",
        example=120.0,
    )
    connect_retry = gui_fields.Timeout(
        minimum=0.1,
        required=False,
        description="The cooling period after failed connect/heartbeat.",
        example=4.0,
    )
    cache = fields.Boolean(
        required=False,
        description="Enable caching.",
        example=True,
    )


class ProxyTCPOutput(BaseSchema):
    port = fields.Integer(
        minimum=1,
        maximum=65535,
        required=False,
        description="The livestatus proxy TCP port.",
        example=6560,
    )
    only_from = fields.List(
        fields.String,
        required=False,
        description="Restrict access to these IP addresses.",
        example=["192.123.32.1", "192.123.32.2"],
    )
    tls = fields.Boolean(
        required=False,
        description="Encrypt TCP Livestatus connections.",
        example=True,
    )


class ProxyAttributesOutput(BaseSchema):
    use_livestatus_daemon = fields.String(
        required=True,
        description="Use livestatus daemon with direct connection or with livestatus proxy.",
        example=True,
    )
    global_settings = fields.Boolean(
        required=False,
        description="When Livestatus proxy daemon is set, you can enable this to use global setting and disable it to use custom parameters.",
        example=True,
    )
    tcp = fields.Nested(
        ProxyTCPOutput,
        required=False,
        description="Allow access via TCP configuration.",
    )
    params = fields.Nested(
        ProxyParamsOutput,
        required=False,
        description="The live status proxy daemon parameters.",
    )


class SocketAttributesOutput(BaseSchema):
    socket_type = fields.String(
        required=True,
        description="The connection name. This can be tcp, tcp6, unix or local.",
        example="tcp",
    )
    path = fields.String(
        required=False,
        description="When the connection name is unix, this is the path to the unix socket.",
        example="/path/to/your/unix_socket",
    )
    host = fields.String(
        required=False,
        description="The IP or domain name of the host.",
        example="127.0.0.1",
    )
    port = fields.Integer(
        required=False,
        description="The TCP port to connect to.",
        example=6792,
    )
    encrypted = fields.Boolean(
        required=False,
        description="To enable an encrypted connection.",
        example=True,
    )
    verify = fields.Boolean(
        required=False,
        description="Verify server certificate.",
        example=True,
    )


class StatusHostAttributes(BaseSchema):
    status_host_set = fields.String(
        required=True,
        description="enabled for 'use the following status host' and disabled for 'no status host'.",
        example=True,
    )
    site = fields.String(
        required=False,
        description="The site ID of the status host.",
        example="prod",
    )
    host = fields.String(
        required=False,
        description="The host name of the status host.",
        example="host_1",
    )


class BasicSettingsAttributes(BaseSchema):
    site_id = fields.String(
        required=True,
        description="The site id.",
        example="prod",
    )
    alias = fields.String(
        required=True,
        description="The alias of the site.",
        example="Site Alias",
    )
    customer = gui_fields.customer_field()


class StatusConnectionAttributesOutput(BaseSchema):
    connection = fields.Nested(
        SocketAttributesOutput,
        required=True,
        description="When connecting to remote site please make sure that Livestatus over TCP is activated there. You can use UNIX sockets to connect to foreign sites on localhost.",
    )
    proxy = fields.Nested(
        ProxyAttributesOutput,
        required=True,
        description="The Livestatus proxy daemon configuration attributes.",
    )
    connect_timeout = fields.Integer(
        required=True,
        description="The time that the GUI waits for a connection to the site to be established before the site is considered to be unreachable.",
        example=2,
    )
    persistent_connection = fields.Boolean(
        required=False,
        description="If you enable persistent connections then Multisite will try to keep open the connection to the remote sites.",
        example=True,
    )
    url_prefix = fields.String(
        required=False,
        description="The URL prefix will be prepended to links of addons like NagVis when a link to such applications points to a host or service on that site.",
        example="/remote_1/",
    )
    status_host = fields.Nested(
        StatusHostAttributes,
        required=False,
        description="By specifying a status host for each non-local connection you prevent Multisite from running into timeouts when remote sites do not respond.",
    )
    disable_in_status_gui = fields.Boolean(
        required=False,
        description="If you disable a connection, then no data of this site will be shown in the status GUI. The replication is not affected by this, however.",
        example=False,
    )


class UserSyncAttributesOutput(BaseSchema):
    sync_with_ldap_connections = fields.String(
        required=True,
        description="Sync with ldap connections. The options are ldap, all, disabled.",
        example="ldap",
    )
    ldap_connections = fields.List(
        fields.String,
        required=False,
        description="A list of ldap connections.",
        example=["LDAP_1", "LDAP_2"],
    )


class ConfigurationConnectionAttributesOutput(BaseSchema):
    enable_replication = fields.Boolean(
        required=False,
        description="Replication allows you to manage several monitoring sites with a logically centralized setup. Remote sites receive their configuration from the central sites.",
        example=True,
    )
    url_of_remote_site = fields.String(
        required=False,
        description="URL of the remote Checkmk including /check_mk/. This URL is in many cases the same as the URL-Prefix but with check_mk/ appended, but it must always be an absolute URL.",
        example="http://remote_site_1/check_mk/",
    )

    disable_remote_configuration = fields.Boolean(
        required=False,
        description="It is a good idea to disable access to Setup completely on the remote site. Otherwise a user who does not now about the replication could make local changes that are overridden at the next configuration activation.",
        example=True,
    )

    ignore_tls_errors = fields.Boolean(
        required=False,
        description="This might be needed to make the synchronization accept problems with SSL certificates when using an SSL secured connection.",
        example=False,
    )

    direct_login_to_web_gui_allowed = fields.Boolean(
        required=False,
        description="When enabled, this site is marked for synchronisation every time a web GUI related option is changed and users are allowed to login to the web GUI of this site.",
        example=True,
    )

    user_sync = fields.Nested(
        UserSyncAttributesOutput,
        required=False,
        description="By default the users are synchronized automatically in the interval configured in the connection. For example the LDAP connector synchronizes the users every five minutes by default. The interval can be changed for each connection individually in the connection settings. Please note that the synchronization is only performed on the master site in distributed setups by default.",
    )

    replicate_event_console = fields.Boolean(
        required=False,
        description="This option enables the distribution of global settings and rules of the Event Console to the remote site. Any change in the local Event Console settings will mark the site as need sync. A synchronization will automatically reload the Event Console of the remote site.",
        example=True,
    )

    replicate_extensions = fields.Boolean(
        required=False,
        description="If you enable the replication of MKPs then during each Activate Changes MKPs that are installed on your central site and all other files below the ~/local/ directory will be also transferred to the remote site. Note: all other MKPs and files below ~/local/ on the remote site will be removed.",
        example=True,
    )


class SiteConfigAttributes(BaseSchema):
    basic_settings = fields.Nested(
        BasicSettingsAttributes,
    )
    status_connection = fields.Nested(
        StatusConnectionAttributesOutput,
    )
    configuration_connection = fields.Nested(
        ConfigurationConnectionAttributesOutput,
    )
    secret = fields.String(
        required=False,
        description="The shared secret used by the central site to authenticate with the remote site for configuring Checkmk.",
        example="secret",
    )


class SiteConnectionResponse(DomainObject):
    domainType = fields.Constant(
        "site_connection",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        SiteConfigAttributes,
        description="The configuration attributes of a site.",
        example=default_config_example(),
    )


class SiteConnectionResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "site_connection",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(SiteConnectionResponse),
        description="A list of site configuration objects.",
        example=[
            {
                "links": [],
                "domainType": "site_connection",
                "id": "prod",
                "title": "Site Alias",
                "members": {},
                "extensions": default_config_example(),
            }
        ],
    )
