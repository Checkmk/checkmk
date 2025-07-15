#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from marshmallow_oneofschema import OneOfSchema

from cmk import fields
from cmk.gui import fields as gui_fields
from cmk.gui.fields.definitions import Username
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.site_management.common import default_config_example

SITE_ID = {
    "site_id": gui_fields.SiteField(
        presence="ignore",
        required=True,
        description="The site ID.",
        example="prod",
    )
}

SITE_ID_EXISTS = {
    "site_id": gui_fields.SiteField(
        presence="should_exist",
        required=True,
        description="A site ID that exists.",
        example="prod",
    )
}

SITE_ID_DOESNT_EXIST = {
    "site_id": gui_fields.SiteField(
        presence="should_not_exist",
        required=True,
        description="A site ID that doesn't already exist.",
        example="prod",
    )
}


class Heartbeat(BaseSchema):
    interval = fields.Integer(
        minimum=1,
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


class ProxyParams(BaseSchema):
    channels = fields.Integer(
        minimum=2,
        maximum=50,
        required=False,
        description="The number of channels to keep open.",
        example=5,
    )
    heartbeat = fields.Nested(
        Heartbeat,
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


class ProxyTcp(BaseSchema):
    port = gui_fields.NetworkPortNumber(
        required=True,
        description="The TCP port to connect to.",
    )
    only_from = fields.List(
        gui_fields.HostnameOrIP(
            description="The IP or domain name of the host.",
            host_type_allowed="ipv4",
            example="192.168.1.1",
            required=True,
        ),
        required=False,
        description="Restrict access to these IP addresses.",
        example=["192.168.1.23"],
    )
    tls = fields.Boolean(
        required=False,
        description="Encrypt TCP Livestatus connections.",
        example=False,
    )


class UseLiveStatusDaemon(BaseSchema):
    use_livestatus_daemon = fields.String(
        enum=["direct", "with_proxy"],
        required=True,
        description="Use livestatus daemon with direct connection or with livestatus proxy.",
        example=True,
    )


class ProxyAttributes(UseLiveStatusDaemon):
    global_settings = fields.Boolean(
        required=True,
        description="When use_livestatus_daemon is set to 'with_proxy', you can set this to True to use global setting or False to use custom parameters.",
        example=True,
    )
    tcp = fields.Nested(
        ProxyTcp,
        required=False,
        description="Allow access via TCP configuration.",
    )
    params = fields.Nested(
        ProxyParams,
        required=False,
        description="The live status proxy daemon parameters.",
    )


class ProxyOrDirect(OneOfSchema):
    type_field = "use_livestatus_daemon"
    type_field_remove = False
    type_schemas = {
        "direct": UseLiveStatusDaemon,
        "with_proxy": ProxyAttributes,
    }


class SocketType(BaseSchema):
    socket_type = fields.String(
        enum=["tcp", "tcp6", "unix", "local"],
        required=True,
        description="The connection name. This can be tcp, tcp6, unix or local.",
        example="tcp",
    )


class SocketIPAttributes(SocketType):
    port = gui_fields.NetworkPortNumber(
        required=True,
        description="The TCP port to connect to.",
    )
    encrypted = fields.Boolean(
        required=True,
        description="To enable an encrypted connection.",
        example=True,
    )
    verify = fields.Boolean(
        required=False,
        description="Verify server certificate.",
        example=True,
    )


class SocketIP4(SocketIPAttributes):
    host = gui_fields.HostnameOrIP(
        description="The IP or domain name of the host.",
        host_type_allowed="hostname_and_ipv4",
        example="127.0.0.1",
        required=True,
    )


class SocketIP6(SocketIPAttributes):
    host = gui_fields.HostnameOrIP(
        description="The IP or domain name of the host.",
        host_type_allowed="hostname_and_ipv6",
        example="5402:1db8:95a3:0000:0000:9a2e:0480:8334",
        required=True,
    )


class SocketUnixAttributes(SocketType):
    path = gui_fields.UnixPath(
        description="When the connection name is unix, this is the path to the unix socket.",
        example="/path/to/your/unix_socket",
        presence="ignore",
    )


class SocketAttributes(OneOfSchema):
    type_field = "socket_type"
    type_field_remove = False
    type_schemas = {
        "tcp": SocketIP4,
        "tcp6": SocketIP6,
        "unix": SocketUnixAttributes,
        "local": SocketType,
    }


class StatusHostAttributesBase(BaseSchema):
    status_host_set = fields.String(
        enum=["enabled", "disabled"],
        required=True,
        description="enabled for 'use the following status host' and disabled for 'no status host'",
        example=False,
    )


class StatusHostAttributesSet(StatusHostAttributesBase):
    site = gui_fields.SiteField(
        presence="should_exist",
        required=True,
        description="The site ID of the status host.",
        example="prod",
    )
    host = gui_fields.HostField(
        should_exist=True,
        required=True,
        description="The host name of the status host.",
        example="host_1",
    )


class StatusHostSet(OneOfSchema):
    type_field = "status_host_set"
    type_field_remove = False
    type_schemas = {
        "enabled": StatusHostAttributesSet,
        "disabled": StatusHostAttributesBase,
    }


class StatusConnectionAttributes(BaseSchema):
    connection = fields.Nested(
        SocketAttributes,
        required=True,
        description="When connecting to remote site please make sure that Livestatus over TCP is activated there. You can use UNIX sockets to connect to foreign sites on localhost.",
    )
    proxy = fields.Nested(
        ProxyOrDirect,
        required=True,
        description="The Livestatus proxy daemon configuration attributes.",
    )
    connect_timeout = fields.Integer(
        required=True,
        description="The time that the GUI waits for a connection to the site to be established before the site is considered to be unreachable.",
        example=2,
    )
    persistent_connection = fields.Boolean(
        load_default=False,
        description="If you enable persistent connections then Multisite will try to keep open the connection to the remote sites.",
        example=False,
    )
    url_prefix = gui_fields.RelativeUrl(
        required=False,
        load_default="",
        must_endwith_one=["/"],
        description="The URL prefix will be prepended to links of addons like NagVis when a link to such applications points to a host or service on that site.",
        example="/remote_1/",
    )
    status_host = fields.Nested(
        StatusHostSet,
        required=True,
        description="By specifying a status host for each non-local connection you prevent Multisite from running into timeouts when remote sites do not respond.",
    )
    disable_in_status_gui = fields.Boolean(
        load_default=False,
        description="If you disable a connection, then no data of this site will be shown in the status GUI. The replication is not affected by this, however.",
        example=False,
    )


class UserSyncBase(BaseSchema):
    sync_with_ldap_connections = fields.String(
        required=True,
        description="Sync with ldap connections. The options are ldap, all, disabled.",
        example="ldap",
        enum=["ldap", "all", "disabled"],
    )


class UserSyncWithLdapConnection(UserSyncBase):
    ldap_connections = fields.List(
        gui_fields.LDAPConnectionID(presence="should_exist"),
        required=True,
        description="A list of ldap connections.",
        example=["LDAP_1", "LDAP_2"],
    )


class UserSyncAttributes(OneOfSchema):
    type_field = "sync_with_ldap_connections"
    type_field_remove = False
    type_schemas = {
        "ldap": UserSyncWithLdapConnection,
        "all": UserSyncBase,
        "disabled": UserSyncBase,
    }


class ConfigurationConnectionWithoutReplicationAttributes(BaseSchema):
    enable_replication = fields.Constant(
        required=True,
        constant=False,
        description="Replication is disabled.",
        example=False,
    )


class ConfigurationConnectionWithReplicationAttributes(BaseSchema):
    enable_replication = fields.Constant(
        required=True,
        constant=True,
        description="Replication allows you to manage several monitoring sites with a logically centralized setup. Remote sites receive their configuration from the central sites.",
        example=True,
    )
    url_of_remote_site = gui_fields.RelativeUrl(
        must_startwith_one=["https", "http"],
        must_endwith_one=["/check_mk/"],
        required=True,
        description="URL of the remote Checkmk including /check_mk/. This URL is in many cases the same as the URL-Prefix but with check_mk/ appended, but it must always be an absolute URL.",
        example="http://remote_site_1/check_mk/",
    )
    disable_remote_configuration = fields.Boolean(
        required=True,
        description="It is a good idea to disable access to Setup completely on the remote site. Otherwise a user who does not now about the replication could make local changes that are overridden at the next configuration activation.",
        example=True,
    )
    ignore_tls_errors = fields.Boolean(
        required=True,
        description="This might be needed to make the synchronization accept problems with SSL certificates when using an SSL secured connection.",
        example=False,
    )
    direct_login_to_web_gui_allowed = fields.Boolean(
        required=True,
        description="When enabled, this site is marked for synchronisation every time a web GUI related option is changed and users are allowed to login to the web GUI of this site.",
        example=True,
    )
    user_sync = fields.Nested(
        UserSyncAttributes,
        required=True,
        description="By default the users are synchronized automatically in the interval configured in the connection. For example the LDAP connector synchronizes the users every five minutes by default. The interval can be changed for each connection individually in the connection settings. Please note that the synchronization is only performed on the master site in distributed setups by default.",
    )
    replicate_event_console = fields.Boolean(
        required=True,
        description="This option enables the distribution of global settings and rules of the Event Console to the remote site. Any change in the local Event Console settings will mark the site as need sync. A synchronization will automatically reload the Event Console of the remote site.",
        example=True,
    )
    replicate_extensions = fields.Boolean(
        required=True,
        description="If you enable the replication of MKPs then during each Activate Changes MKPs that are installed on your central site and all other files below the ~/local/ directory will be also transferred to the remote site. Note: all other MKPs and files below ~/local/ on the remote site will be removed.",
        example=True,
    )
    message_broker_port = fields.Integer(
        required=True,
        description="The port used by the message broker to exchange messages.",
        example=5672,
    )


class ConfigurationConnectionAttributes(OneOfSchema):
    type_field = "enable_replication"
    type_field_remove = False
    type_schemas = {
        "WithReplication": ConfigurationConnectionWithReplicationAttributes,
        "WithoutReplication": ConfigurationConnectionWithoutReplicationAttributes,
    }

    def get_data_type(self, data):
        if "enable_replication" not in data:
            return None

        return "WithReplication" if data["enable_replication"] else "WithoutReplication"


class SiteLoginRequest(BaseSchema):
    username = Username(
        required=True,
        description="An administrative user's username.",
        example="cmkadmin",
    )
    password = fields.String(
        required=True,
        description="The password for the username given",
        example="password",
    )


class BasicSettingsAttributes(BaseSchema):
    alias = fields.String(
        required=True,
        description="The alias of the site.",
        example="Site Alias",
    )
    customer = gui_fields.customer_field()


class BasicSettingsAttributesCreate(BasicSettingsAttributes):
    site_id = gui_fields.SiteField(
        presence="should_not_exist",
        required=True,
        description="The site ID.",
        example="prod",
    )


class BasicSettingsAttributesUpdate(BasicSettingsAttributes):
    site_id = gui_fields.SiteField(
        presence="should_exist",
        required=True,
        description="The site ID.",
        example="prod",
    )


class SiteConfigAttributes(BaseSchema):
    status_connection = fields.Nested(
        StatusConnectionAttributes,
        required=True,
    )
    configuration_connection = fields.Nested(
        ConfigurationConnectionAttributes,
        required=True,
    )
    secret = fields.String(
        required=False,
        description="The shared secret used by the central site to authenticate with the remote site for configuring Checkmk.",
        example="secret",
    )


class SiteConfigAttributesCreate(SiteConfigAttributes):
    basic_settings = fields.Nested(
        BasicSettingsAttributesCreate,
        required=True,
    )


class SiteConfigAttributesUpdate(SiteConfigAttributes):
    basic_settings = fields.Nested(
        BasicSettingsAttributesUpdate,
        required=True,
    )


class SiteConnectionRequestCreate(BaseSchema):
    site_config = fields.Nested(
        SiteConfigAttributesCreate,
        required=True,
        description="A site's connection.",
        example=default_config_example(),
    )


class SiteConnectionRequestUpdate(BaseSchema):
    site_config = fields.Nested(
        SiteConfigAttributesUpdate,
        required=True,
        description="A site's connection.",
        example=default_config_example(),
    )
