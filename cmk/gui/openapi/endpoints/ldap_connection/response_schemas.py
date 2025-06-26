#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from marshmallow import post_dump
from marshmallow_oneofschema import OneOfSchema

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection
from cmk.gui.userdb import get_user_attributes, UserRolesConfigFile

from cmk import fields


class LDAPCheckbox(BaseSchema):
    state = fields.String(
        description="",
        example="enabled",
        enum=["enabled", "disabled"],
    )


class LDAPGeneralProperties(BaseSchema):
    id = fields.String(
        description="The LDAP connection ID.",
    )
    description = fields.String(
        description="Add a title or describe this rule",
    )
    comment = fields.String(
        description="An optional comment to explain the purpose of this object. The comment "
        "is only visible in this dialog and can help other users to understand the intentions "
        "of the configured attributes."
    )
    documentation_url = fields.String(
        description="An optional URL linking documentation or any other page. An icon links to "
        "the page and opens in a new tab when clicked. You can use either global URLs (starting"
        " with http://), absolute local URLs (starting with /) or relative URLs (relative to check_mk/).",
    )
    rule_activation = fields.String(
        enum=["activated", "deactivated"],
        description="Selecting 'deactivated' will disable the rule, but it will remain in the "
        "configuration.",
    )


class LDAPDirectoryTypeConnection(BaseSchema):
    type = fields.String(
        enum=[
            "active_directory_manual",
            "active_directory_automatic",
            "open_ldap",
            "389_directory_server",
        ],
        description="",
        example="active_directory_manual",
    )
    ldap_server = fields.String(
        description="Set the host address of the LDAP server. Might be an IP address or "
        "resolvable host name.",
        example="your_ldap_server.example.com",
    )
    failover_servers = fields.List(
        fields.String,
        description="When the connection to the first server fails with connect specific "
        "errors like timeouts or some other network related problems, the connect mechanism "
        "will try to use this server instead of the server configured above. If you use "
        "persistent connections (default), the connection is being used until the LDAP is "
        "not reachable or the local webserver is restarted. You may paste a text from your "
        "clipboard which contains several parts separated by ';' characters into the last "
        "input field. The text will then be split by these separators and the single parts "
        "are added into dedicated input fields.",
        example=["192.168.5.2", "195.65.2.8"],
    )
    domain = fields.String(
        description="Configure the DNS domain name of your Active directory domain here, "
        "Checkmk will then query this domain for it's closest domain controller to communicate "
        "with.",
        example="your_domain.com",
    )


class LDAPBindCredentials(LDAPCheckbox):
    type = fields.String(
        enum=["explicit", "store"],
        description="A specific password or a password store id",
        example="explicit",
    )
    bind_dn = fields.String(
        description="The distinguished name of the user account which is used to bind to the "
        "LDAP server. This user account must have read access to the LDAP directory.",
        example="CN=bind_user,OU=users,DC=example,DC=com",
    )
    explicit_password = fields.String(
        description="An explicit password of the user account which is used to bind to the "
        "LDAP server. This user account must have read access to the LDAP directory.",
        example="your_password",
    )
    password_store_id = fields.String(
        description="A password store id from the user account which is used to bind to the "
        "LDAP server. This user account must have read access to the LDAP directory.",
        example="",
    )


class LDAPTCPPort(LDAPCheckbox):
    port = fields.Integer(
        description="",
        example=389,
    )


class LDAPConnectTimeout(LDAPCheckbox):
    seconds = fields.Float(
        description="Timeout for the initial connection to the LDAP server in seconds.",
        example=2.0,
    )


class LDAPVersion(LDAPCheckbox):
    version = fields.Integer(
        enum=[2, 3],
        description="The selected LDAP version the LDAP server is serving. Most modern "
        "servers use LDAP version 3.",
        example=3,
    )


class LDAPPageSize(LDAPCheckbox):
    size = fields.Integer(
        description="LDAP searches can be performed in paginated mode, for example to "
        "improve the performance. This enables pagination and configures the size of "
        "the pages.",
        example=1000,
    )


class LDAPResponseTimeout(LDAPCheckbox):
    seconds = fields.Integer(
        description="Timeout for the initial connection to the LDAP server in seconds.",
        example=5,
    )


class LDAPConnectionSuffix(LDAPCheckbox):
    suffix = fields.String(
        description="The LDAP connection suffix can be used to distinguish equal named"
        " objects (name conflicts), for example user accounts, from different LDAP "
        "connections.",
        example="suffix_example",
    )


class LDAPConnection(BaseSchema):
    directory_type = fields.Nested(
        LDAPDirectoryTypeConnection,
        description="The credentials to be used to connect to the LDAP server. The used "
        "account must not be allowed to do any changes in the directory the whole connection "
        "is read only. In some environment an anonymous connect/bind is allowed, in this case "
        "you don't have to configure anything here.It must be possible to list all needed user "
        "and group objects from the directory.",
        example={
            "type": "active_directory_manual",
            "ldap_server": "your_ldap_server.example.com",
            "failover_servers": ["192.168.5.2", "195.65.2.8"],
        },
    )
    bind_credentials = fields.Nested(
        LDAPBindCredentials,
        description="The credentials used to connect to the LDAP server.",
        example={
            "state": "enabled",
            "type": "store",
            "bind_dn": "CN=bind_user,OU=users,DC=example,DC=com",
            "password_store_id": "pw_store_id",
        },
    )
    tcp_port = fields.Nested(
        LDAPTCPPort,
        description="The TCP port to be used to connect to the LDAP server.",
        example={"state": "enabled", "port": 389},
    )
    ssl_encryption = fields.String(
        enum=["enable_ssl", "disable_ssl"],
        description="Connect to the LDAP server with a SSL encrypted connection. The trusted "
        "certificates authorities configured in Checkmk will be used to validate the certificate "
        "provided by the LDAP server.",
        example="enable_ssl",
    )
    connect_timeout = fields.Nested(
        LDAPConnectTimeout,
        description="If the connection timeout is set and its value.",
        example={"state": "enabled", "seconds": 2.0},
    )
    ldap_version = fields.Nested(
        LDAPVersion,
        description="If the ldap version is set and the version it's set to. Either 2 or 3.",
        example={"state": "enabled", "version": 3},
    )
    page_size = fields.Nested(
        LDAPPageSize,
        description="If the page size is enabled and its value.",
        example={"state": "enabled", "size": 1000},
    )
    response_timeout = fields.Nested(
        LDAPResponseTimeout,
        description="Enable the response timeout and define its value.",
        example={"state": "enabled", "seconds": 5},
    )
    connection_suffix = fields.Nested(
        LDAPConnectionSuffix,
        description="If the connection suffix is enabled and what its set to.",
        example={"state": "enabled", "suffix": "suffix_example"},
    )


class LDAPUserSearchFilter(LDAPCheckbox):
    filter = fields.String(
        description="Using this option you can define an optional LDAP filter which is used "
        "during LDAP searches. It can be used to only handle a subset of the users below the given base DN.",
        example="(&(objectclass=user)(objectcategory=person))",
    )


class LDAPUserGroupFilter(LDAPCheckbox):
    filter = fields.String(
        description="Define the DN of a group object which is used to filter the users.",
        example="CN=cmk-users,OU=groups,DC=example,DC=com",
    )


class LDAPUserIDAttribute(LDAPCheckbox):
    attribute = fields.String(
        description="The attribute used to identify the individual users. It must have unique "
        "values to make an user identifyable by the value of this attribute.",
        example="attribute_example",
    )


class LDAPUsers(BaseSchema):
    user_base_dn = fields.String(
        description="Give a base distinguished name here. All user accounts to synchronize "
        "must be located below this one.",
        example="OU=users,DC=example,DC=com",
    )
    search_scope = fields.String(
        enum=[
            "search_whole_subtree",
            "search_only_base_dn_entry",
            "search_all_one_level_below_base_dn",
        ],
        description="Scope to be used in LDAP searches. In most cases Search whole subtree below "
        "the base DN is the best choice. It searches for matching objects recursively.",
        example="search_whole_subtree",
    )
    search_filter = fields.Nested(
        LDAPUserSearchFilter,
        description="Enable and define an optional LDAP filter.",
        example={
            "state": "enabled",
            "filter": "(&(objectclass=user)(objectcategory=person))",
        },
    )
    filter_group = fields.Nested(
        LDAPUserGroupFilter,
        description="Enable and define the DN of a group object which is used to filter the users.",
        example={
            "state": "enabled",
            "filter": "CN=cmk-users,OU=groups,DC=example,DC=com",
        },
    )
    user_id_attribute = fields.Nested(
        LDAPUserIDAttribute,
        description="Enable and define a user ID attribute.",
        example={"state": "enabled", "attribute": "attribute_example"},
    )
    user_id_case = fields.String(
        enum=["dont_convert_to_lowercase", "convert_to_lowercase"],
        description="Convert imported User-IDs to lower case during synchronization or leave as is.",
        example="convert_to_lowercase",
    )
    umlauts_in_user_ids = fields.String(
        enum=["keep_umlauts", "replace_umlauts"],
        description="Checkmk does not support special characters in User-IDs. However, to deal with "
        "LDAP users having umlauts in their User-IDs you previously had the choice to replace umlauts "
        "with other characters. This option is still available for backward compatibility, but you are "
        "advised to use the 'keep_umlauts' option for new installations.",
        example="keep_umlauts",
    )
    create_users = fields.String(
        enum=["on_login", "on_sync"],
        description="Create user accounts during sync or on the first login",
        example="on_sync",
    )


class LDAPGroupSearchFilter(LDAPCheckbox):
    filter = fields.String(
        description="Define an optional LDAP filter which is used during group related LDAP searches. "
        "It can be used to only handle a subset of the groups below the given group base DN.",
        example="(objectclass=group)",
    )


class LDAPMemberAttributeValue(LDAPCheckbox):
    attribute = fields.String(
        description="The attribute used to identify users group memberships.",
        example="example_member",
    )


class LDAPGroups(BaseSchema):
    group_base_dn = fields.String(
        description="Give a base distinguished name here. All groups used must be located below this one.",
        example="OU=groups,DC=example,DC=com",
    )
    search_scope = fields.String(
        enum=[
            "search_whole_subtree",
            "search_only_base_dn_entry",
            "search_all_one_level_below_base_dn",
        ],
        description="Scope to be used in group related LDAP searches. In most cases Search whole subtree "
        "below the base DN is the best choice. It searches for matching objects in the given base recursively.",
        example="",
    )
    search_filter = fields.Nested(
        LDAPGroupSearchFilter,
        description="Enable and define an optional LDAP filter.",
        example={"state": "enabled", "filter": "(objectclass=group)"},
    )
    member_attribute = fields.Nested(
        LDAPMemberAttributeValue,
        description="Enable and define a member attribute.",
        example={"state": "enabled", "attribute": "example_member"},
    )


class LDAPSyncPluginAlias(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute containing the alias of the user.",
    )


class LDAPSyncPluginAuthExp(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="When the value of this attribute changes for a user account, all current authenticated "
        "sessions of the user are invalidated and the user must login again. By default this field uses the "
        "fields which hold the time of the last password change of the user.",
    )


class LDAPSyncPluginDisableNotifications(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginEmailAddress(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute containing the mail address of the user.",
    )


class LDAPSyncPluginMenuIcons(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginNavBarIcons(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginPager(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute containing the pager number of the user.",
    )


class LDAPSyncPluginShowMode(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginSideBarPosition(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginStartURL(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginTempUnit(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginUITheme(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPSyncPluginVisibilityOfHostsOrServices(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
    )


class LDAPContactGroupMembership(LDAPCheckbox):
    handle_nested = fields.Boolean(
        description="When enabled, this plug-in will not only handle direct group memberships, "
        "instead it will also dig into nested groups and treat the members of those groups as "
        "contact group members as well. Please bear in mind that this feature might increase the "
        "execution time of your LDAP sync.",
    )
    sync_from_other_connections = fields.List(
        fields.String,
        description="This is a special feature for environments where user accounts are located "
        "in one LDAP directory and groups objects having them as members are located in other "
        "directories. You should only enable this feature when you are in this situation and "
        "really need it. The current connection is always used.",
    )


class LDAPFromToFields(LDAPCheckbox):
    from_time = gui_fields.Timestamp(
        required=True,
        example="2024-02-29T17:32:28+00:00",
    )
    to_time = gui_fields.Timestamp(
        required=True,
        example="2024-02-29T12:53:34+00:00",
    )


class LDAPDisableNotificationsValue(BaseSchema):
    temporarily_disable_all_notifications = fields.Boolean(
        description="When this option is active you will not get any alerts or other notifications "
        "via email, SMS or similar. This overrides all other notification settings and rules, so "
        "make sure that you know what you are doing.",
        example=True,
    )
    custom_time_range = fields.Nested(
        LDAPFromToFields,
        description="Here you can specify a time range where no notifications are generated.",
        example={
            "from_time": "2024-02-29T17:32:28+00:00",
            "to_time": "2024-02-29T12:53:34+00:00",
        },
    )


class LDAPGroupsToSyncBase(BaseSchema):
    group_cn = fields.String(
        description="The common name of the group in LDAP. This is the name of the group as it is "
        "stored in the LDAP directory.",
        example="group_cn_example",
    )
    attribute_to_set = fields.String(
        description="The name of the attribute to set.",
    )


class LDAPGroupsToSyncDisableNotifications(LDAPGroupsToSyncBase):
    value = fields.Nested(
        LDAPDisableNotificationsValue,
        description="The value of the attribute to set",
        example="",
    )


class LDAPGroupsToSyncStartURL(LDAPGroupsToSyncBase):
    value = fields.String(
        description="The URL that the user should be redirected to after login. There is a "
        "'default_start_url', a 'welcome_page', and any other will be treated as a custom URL",
        example="default_start_url",
    )


class LDAPGroupsToSyncAllOthers(LDAPGroupsToSyncBase):
    value = fields.String(
        description="The value of the attribute to set",
        example="",
    )


class LDAPGroupsToSyncSelector(OneOfSchema):
    type_field_remove = False
    type_field = "attribute_to_set"
    type_schemas = {
        "disable_notifications": LDAPGroupsToSyncDisableNotifications,
        "start_url": LDAPGroupsToSyncStartURL,
    }

    def get_obj_type(self, obj):
        attribute_to_set = obj.get("attribute_to_set")
        if attribute_to_set not in self.type_schemas:
            self.type_schemas[attribute_to_set] = LDAPGroupsToSyncAllOthers
        return attribute_to_set


class LDAPGroupsToAttributes(LDAPCheckbox):
    handle_nested = fields.Boolean(
        description="Once you enable this option, this plug-in will not only handle direct group "
        "memberships, instead it will also dig into nested groups and treat the members of those "
        "groups as contact group members as well. Please bear in mind that this feature might increase the "
        "execution time of your LDAP sync. (Active Directory only at the moment)",
    )
    sync_from_other_connections = fields.List(
        fields.String,
        description="This is a special feature for environments where user accounts are located in "
        "one LDAP directory and groups objects having them as members are located in other directories. "
        "You should only enable this feature when you are in this situation and really need it. The "
        "current connection is always used.",
    )
    groups_to_sync = fields.List(
        fields.Nested(LDAPGroupsToSyncSelector),
        description="Specify the groups to control the value of a given user attribute. If a user is "
        "not a member of a group, the attribute will be left at its default value. When a single "
        "attribute is set by multiple groups and a user is a member of multiple of these groups, the "
        "later plug-in in the list will override the others.",
        example=[
            {
                "group_cn": "group_cn_example",
                "attribute_to_set": "main_menu_icons",
                "value": "main_menu_icons",
            }
        ],
    )


class LDAPRoleElement(LDAPCheckbox):
    group_dn = fields.String(
        description="This group must be defined within the scope of the LDAP Group Settings",
        example="cmk-users",
    )
    search_in = fields.String(
        description="An existing ldap connection.",
        example="LDAP_1",
    )


class LDAPGroupsToRoles(LDAPCheckbox):
    handle_nested = fields.Boolean(
        description="Once you enable this option, this plug-in will not only handle direct group "
        "memberships, instead it will also dig into nested groups and treat the members of those "
        "groups as contact group members as well. Please bear in mind that this feature might "
        "increase the execution time of your LDAP sync",
    )
    admin = fields.List(fields.Nested(LDAPRoleElement))
    agent_registration = fields.List(fields.Nested(LDAPRoleElement))
    guest = fields.List(fields.Nested(LDAPRoleElement))
    user = fields.List(fields.Nested(LDAPRoleElement))

    @post_dump(pass_original=True)
    def _include_other_user_roles(
        self,
        result_data: dict[str, Any],
        original_data: dict[str, Any],
        *,
        many: bool = False,
    ) -> dict[str, Any]:
        for field in self.fields:
            original_data.pop(field, None)

        if not original_data:
            return result_data

        userroles = UserRolesConfigFile().load_for_reading()
        for role, value in original_data.items():
            if role in userroles:
                result_data[role] = value

        return result_data


class LDAPSyncPlugins(BaseSchema):
    alias = fields.Nested(
        LDAPSyncPluginAlias,
        description="Populates the alias attribute of the Setup user by synchronizing an attribute "
        "from the LDAP user account. By default the LDAP attribute cn is used.",
    )
    authentication_expiration = fields.Nested(
        LDAPSyncPluginAuthExp,
        description="This plug-in fetches all information which are needed to check whether or not an "
        "already authenticated user should be deauthenticated, e.g. because the password has changed "
        "in LDAP or the account has been locked.",
    )
    disable_notifications = fields.Nested(
        LDAPSyncPluginDisableNotifications,
        description="When this option is active you will not get any alerts or other notifications "
        "via email, SMS or similar. This overrides all other notification settings and rules, so make "
        "sure that you know what you do. Moreover you can specify a time range where no notifications "
        "are generated.",
    )
    email_address = fields.Nested(
        LDAPSyncPluginEmailAddress,
        description="Synchronizes the email of the LDAP user account into Checkmk",
    )
    main_menu_icons = fields.Nested(
        LDAPSyncPluginMenuIcons,
        description="In the main menus you can select between two options: Have a green icon only for "
        "the headlines – the 'topics' – for lean design. Or have a colored icon for every entry so that "
        "over time you can zoom in more quickly to a specific entry.",
    )
    navigation_bar_icons = fields.Nested(
        LDAPSyncPluginNavBarIcons,
        description="With this option you can define if icons in the navigation bar should show a title "
        "or not. This gives you the possibility to save some space in the UI.",
    )
    pager = fields.Nested(
        LDAPSyncPluginPager,
        description="This plug-in synchronizes a field of the users LDAP account to the pager attribute "
        "of the Setup user accounts, which is then forwarded to the monitoring core and can be used for "
        "notifications. By default the LDAP attribute mobile is used.",
    )
    show_mode = fields.Nested(
        LDAPSyncPluginShowMode,
        description="In some places like e.g. the main menu Checkmk divides features, filters, input "
        "fields etc. in two categories, showing more or less entries. With this option you can set a "
        "default mode for unvisited menus. Alternatively, you can enforce to show more, so that the "
        "round button with the three dots is not shown at all.",
    )
    ui_sidebar_position = fields.Nested(
        LDAPSyncPluginSideBarPosition,
        description="The sidebar position",
    )
    start_url = fields.Nested(
        LDAPSyncPluginStartURL,
        description="The start URL to display in main frame.",
    )
    temperature_unit = fields.Nested(
        LDAPSyncPluginTempUnit,
        description="Set the temperature unit used for graphs and perfometers. The default unit can "
        "be configured here. Note that this setting does not affect the temperature unit used in "
        "service outputs, which can however be configured in this ruleset.",
    )
    ui_theme = fields.Nested(
        LDAPSyncPluginUITheme,
        description="The user interface theme",
    )
    visibility_of_hosts_or_services = fields.Nested(
        LDAPSyncPluginVisibilityOfHostsOrServices,
        description="When this option is checked, the status GUI will only display hosts and "
        "services that the user is a contact for - even if they have the permission for seeing all objects.",
    )
    contact_group_membership = fields.Nested(
        LDAPContactGroupMembership,
        description="Adds the user to contact groups based on the group memberships in LDAP. This plug-in "
        "adds the user only to existing contact groups while the name of the contact group must match the "
        "common name (cn) of the LDAP group.",
    )
    groups_to_custom_user_attributes = fields.Nested(
        LDAPGroupsToAttributes,
        description="Sets custom user attributes based on the group memberships in LDAP. This plug-in can "
        "be used to set custom user attributes to specified values for all users which are member of a "
        "group in LDAP. The specified group name must match the common name (CN) of the LDAP group.",
    )
    groups_to_roles = fields.Nested(
        LDAPGroupsToRoles,
        description="Configures the roles of the user depending on its group memberships in LDAP.",
    )

    @post_dump(pass_original=True)
    def _include_custom_user_attributes(
        self,
        result_data: dict[str, Any],
        original_data: dict[str, Any],
        *,
        many: bool = False,
    ) -> dict[str, Any]:
        for field in self.fields:
            original_data.pop(field, None)

        if not original_data:
            return result_data

        custom_attributes = [name for name, attr in get_user_attributes() if attr.is_custom()]
        for field, value in original_data.items():
            if field in custom_attributes:
                result_data[field] = value

        return result_data


class CustomSyncPlugin(LDAPCheckbox):
    attribute_to_sync = fields.String(
        description="A custom user attribute.",
    )


class LDAPSyncInterval(BaseSchema):
    days = fields.Integer()
    hours = fields.Integer()
    minutes = fields.Integer()


class LDAPOther(BaseSchema):
    sync_interval = fields.Nested(
        LDAPSyncInterval,
        description="This option defines the interval of the LDAP synchronization. This setting "
        "is only used by sites which have the automatic user synchronization enabled.",
    )


class LDAPConnectionConfig(BaseSchema):
    general_properties = fields.Nested(LDAPGeneralProperties)
    ldap_connection = fields.Nested(LDAPConnection)
    users = fields.Nested(LDAPUsers)
    groups = fields.Nested(LDAPGroups)
    sync_plugins = fields.Nested(LDAPSyncPlugins)
    other = fields.Nested(LDAPOther)


ldap_config_example: dict[str, dict[str, Any]] = {
    "general_properties": {
        "id": "LDAP_1",
        "description": "",
        "comment": "",
        "documentation_url": "",
        "rule_activation": "activated",
    },
    "ldap_connection": {
        "directory_type": {
            "type": "active_directory_manual",
            "ldap_server": "123.31.12.34",
            "failover_servers": [],
        },
        "bind_credentials": {"state": "disabled"},
        "tcp_port": {"state": "disabled"},
        "ssl_encryption": "disable_ssl",
        "connect_timeout": {"state": "disabled"},
        "ldap_version": {"state": "disabled"},
        "page_size": {"state": "disabled"},
        "response_timeout": {"state": "disabled"},
        "connection_suffix": {"state": "disabled"},
    },
    "users": {
        "user_base_dn": "",
        "search_scope": "search_only_base_dn_entry",
        "search_filter": {"state": "disabled"},
        "filter_group": {"state": "disabled"},
        "user_id_attribute": {"state": "disabled"},
        "user_id_case": "dont_convert_to_lowercase",
        "umlauts_in_user_ids": "keep_umlauts",
        "create_users": "on_login",
    },
    "groups": {
        "group_base_dn": "",
        "search_scope": "search_whole_subtree",
        "search_filter": {"state": "disabled"},
        "member_attribute": {"state": "disabled"},
    },
    "sync_plugins": {
        "alias": {"state": "disabled"},
        "authentication_expiration": {"state": "disabled"},
        "disable_notifications": {"state": "disabled"},
        "email_address": {"state": "disabled"},
        "main_menu_icons": {"state": "disabled"},
        "navigation_bar_icons": {"state": "disabled"},
        "pager": {"state": "disabled"},
        "show_mode": {"state": "disabled"},
        "ui_sidebar_position": {"state": "disabled"},
        "start_url": {"state": "disabled"},
        "temperature_unit": {"state": "disabled"},
        "ui_theme": {"state": "disabled"},
        "visibility_of_hosts_or_services": {"state": "disabled"},
        "contact_group_membership": {"state": "disabled"},
        "groups_to_custom_user_attributes": {"state": "disabled"},
        "groups_to_roles": {"state": "disabled"},
    },
    "other": {"sync_interval": {"days": 5, "hours": 2, "minutes": 30}},
}


class LDAPConnectionResponse(DomainObject):
    domainType = fields.Constant(
        "ldap_connection",
        description="The domain type of the object.",
    )
    extensions = fields.Nested(
        LDAPConnectionConfig,
        description="The configuration attributes of a user LDAP connection.",
        example=ldap_config_example,
    )


class LDAPConnectionResponseCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "ldap_connection",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(LDAPConnectionResponse),
        description="A list of LDAP connections.",
        example=[
            {
                "links": [],
                "domainType": "ldap_connection",
                "id": "LDAP_1",
                "title": "",
                "members": {},
                "extensions": ldap_config_example,
            }
        ],
    )
