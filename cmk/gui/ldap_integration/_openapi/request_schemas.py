#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="mutable-override"

# mypy: disable-error-code="no-untyped-def"

from collections.abc import MutableMapping
from typing import Any, override

from marshmallow import INCLUDE, post_load, pre_load, ValidationError
from marshmallow_oneofschema.one_of_schema import OneOfSchema

from cmk import fields
from cmk.gui.fields import LDAPConnectionID, Timestamp
from cmk.gui.fields.base import ValueTypedDictSchema
from cmk.gui.fields.custom_fields import LDAPConnectionSuffix
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.endpoints.utils import mutually_exclusive_fields
from cmk.gui.userdb import get_ldap_connections, UserRolesConfigFile
from cmk.gui.watolib.custom_attributes import load_custom_attrs_from_mk_file


class LDAPCheckboxDisabledRequest(BaseSchema):
    state = fields.Constant(
        "disabled",
        description="This config parameter is disabled.",
        example="disabled",
        load_default="disabled",
    )


class LDAPCheckboxEnabledRequest(BaseSchema):
    state = fields.Constant(
        "enabled",
        description="This config parameter is enabled.",
        example="enabled",
        required=True,
    )


class LDAPCheckboxSelector(OneOfSchema):
    type_field = "state"
    type_field_remove = False

    @override
    def get_obj_type(self, obj):
        return obj["state"]


class LDAPGeneralPropertiesRequest(BaseSchema):
    description = fields.String(
        description="Add a title or describe this rule",
        load_default="",
    )
    comment = fields.String(
        description="An optional comment to explain the purpose of this object. The comment is only"
        " visible in this dialog and can help other users to understand the intentions of the configured attributes.",
        load_default="",
    )
    documentation_url = fields.String(
        description="An optional URL linking documentation or any other page. An icon links to the "
        "page and opens in a new tab when clicked. You can use either global URLs (starting with http://)"
        ", absolute local URLs (starting with /) or relative URLs (relative to check_mk/).",
        load_default="",
    )
    rule_activation = fields.String(
        enum=["activated", "deactivated"],
        description="Selecting 'deactivated' will disable the rule, but it will remain in the configuration.",
        load_default="activated",
    )


class LDAPGeneralPropertiesCreateRequest(LDAPGeneralPropertiesRequest):
    id = LDAPConnectionID(presence="should_not_exist")


class LDAPGeneralPropertiesUpdateRequest(LDAPGeneralPropertiesRequest):
    id = LDAPConnectionID(presence="should_exist")


class DirectoryTypeBaseRequest(BaseSchema):
    type = fields.String(
        enum=[
            "active_directory_manual",
            "active_directory_automatic",
            "open_ldap",
            "389_directory_server",
        ],
        description="Select the software the LDAP directory is based on.",
        example="active_directory_manual",
        required=True,
    )


class DirectoryTypeManualRequest(DirectoryTypeBaseRequest):
    ldap_server = fields.String(
        description="Set the host address of the LDAP server. Might be an IP address or resolvable host name.",
        example="your_ldap_server.example.com",
        required=True,
    )
    failover_servers = fields.List(
        fields.String,
        description="When the connection to the first server fails with connect specific errors like timeouts"
        " or some other network related problems, the connect mechanism will try to use this server instead "
        "of the server configured above. If you use persistent connections (default), the connection is being"
        " used until the LDAP is not reachable or the local webserver is restarted. You may paste a text from"
        " your clipboard which contains several parts separated by ';' characters into the last input field. "
        "The text will then be split by these separators and the single parts are added into dedicated input fields.",
        example=["192.168.5.2", "195.65.2.8"],
        load_default=[],
    )


class DirectoryTypeAutoRequest(DirectoryTypeBaseRequest):
    domain = fields.String(
        description="Configure the DNS domain name of your Active directory domain here, Checkmk will then "
        "query this domain for it's closest domain controller to communicate with.",
        example="your_domain.com",
        required=True,
    )


class DirectoryTypeSelectorRequest(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "active_directory_manual": DirectoryTypeManualRequest,
        "active_directory_automatic": DirectoryTypeAutoRequest,
        "open_ldap": DirectoryTypeManualRequest,
        "389_directory_server": DirectoryTypeManualRequest,
    }


class BindCredentialsBaseRequest(LDAPCheckboxEnabledRequest):
    bind_dn = fields.String(
        description="The distinguished name of the user account which is used to bind to the LDAP server."
        " This user account must have read access to the LDAP directory.",
        example="CN=bind_user,OU=users,DC=example,DC=com",
        load_default="",
    )


class BindCredentialsStoreIdRequest(BindCredentialsBaseRequest):
    type = fields.Constant("store", required=True)
    password_store_id = fields.String(
        description="A password store id from the user account which is used to bind to the LDAP server."
        " This user account must have read access to the LDAP directory.",
        example="your_password_store_id",
        required=True,
    )


class BindCredentialsExplicitPasswordRequest(BindCredentialsBaseRequest):
    type = fields.Constant("explicit", required=True)
    explicit_password = fields.String(
        description="An explicit password of the user account which is used to bind to the LDAP server."
        " This user account must have read access to the LDAP directory.",
        example="your_password",
        required=True,
    )


class BindCredentialsPasswordTypeSelectorRequest(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "store": BindCredentialsStoreIdRequest,
        "explicit": BindCredentialsExplicitPasswordRequest,
    }


class BindCredentialsSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": BindCredentialsPasswordTypeSelectorRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPTCPPortRequest(LDAPCheckboxEnabledRequest):
    port = fields.Integer(
        description="This variable allows you to specify the TCP port to be used"
        " to connect to the LDAP server.",
        example=389,
        load_default=389,
    )


class LDAPTCPPortSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPTCPPortRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPConnectTimeoutRequest(LDAPCheckboxEnabledRequest):
    seconds = fields.Float(
        description="Timeout for the initial connection to the LDAP server in seconds.",
        example=2.0,
        load_default=2.0,
    )


class LDAPConnectTimeoutSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPConnectTimeoutRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPVersionRequest(LDAPCheckboxEnabledRequest):
    version = fields.Integer(
        enum=[2, 3],
        description="The selected LDAP version the LDAP server is serving."
        " Most modern servers use LDAP version 3.",
        example=3,
        load_default=3,
    )


class LDAPVersionSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPVersionRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPPageSizeRequest(LDAPCheckboxEnabledRequest):
    size = fields.Integer(
        description="LDAP searches can be performed in paginated mode, for example to "
        "improve the performance. This enables pagination and configures the size of the pages.",
        example=1000,
        load_default=1000,
    )


class LDAPPageSizeSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPPageSizeRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPResponseTimeoutRequest(LDAPCheckboxEnabledRequest):
    seconds = fields.Integer(
        description="Timeout for the initial connection to the LDAP server in seconds.",
        example=5,
        load_default=5,
    )


class LDAPResponseTimeoutSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPResponseTimeoutRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPConnectionSuffixCreateRequest(LDAPCheckboxEnabledRequest):
    suffix = LDAPConnectionSuffix(
        presence="should_not_exist",
        example="suffix_example",
        required=True,
    )


class LDAPConnectionSuffixCreateSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPConnectionSuffixCreateRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPConnectionSuffixUpdateRequest(LDAPCheckboxEnabledRequest):
    suffix = fields.String(
        description="The LDAP connection suffix can be used to distinguish equal named objects"
        " (name conflicts), for example user accounts, from different LDAP connections.",
        example="suffix_example",
        required=True,
    )


class LDAPConnectionSuffixUpdateSelectorRequest(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPConnectionSuffixUpdateRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPConnectionRequest(BaseSchema):
    directory_type = fields.Nested(
        DirectoryTypeSelectorRequest,
        description="The credentials to be used to connect to the LDAP server. The used account"
        " must not be allowed to do any changes in the directory the whole connection is read only."
        " In some environment an anonymous connect/bind is allowed, in this case you don't have to "
        "configure anything here.It must be possible to list all needed user and group objects from"
        " the directory.",
        example={
            "type": "active_directory_manual",
            "ldap_server": "your_ldap_server.example.com",
            "failover_servers": ["192.168.5.2", "195.65.2.8"],
        },
        required=True,
    )
    bind_credentials = fields.Nested(
        BindCredentialsSelectorRequest,
        description="The credentials used to connect to the LDAP server.",
        example={
            "state": "enabled",
            "bind_dn": "CN=bind_user,OU=users,DC=example,DC=com",
            "password_store_id": "pw_store_id",
        },
        load_default={"state": "disabled"},
    )
    tcp_port = fields.Nested(
        LDAPTCPPortSelectorRequest,
        description="The TCP port to be used to connect to the LDAP server.",
        example={"state": "enabled", "port": 389},
        load_default={"state": "disabled"},
    )
    ssl_encryption = fields.String(
        enum=["enable_ssl", "disable_ssl"],
        description="Connect to the LDAP server with a SSL encrypted connection. The trusted "
        "certificates authorities configured in Checkmk will be used to validate the certificate"
        " provided by the LDAP server.",
        example="enable_ssl",
        load_default="disable_ssl",
    )
    connect_timeout = fields.Nested(
        LDAPConnectTimeoutSelectorRequest,
        description="If the connection timeout is set and its value.",
        example={"state": "enabled", "seconds": 2.0},
        load_default={"state": "disabled"},
    )
    ldap_version = fields.Nested(
        LDAPVersionSelectorRequest,
        description="If the ldap version is set and the version it's set to.",
        example={"state": "enabled", "version": 3},
        load_default={"state": "disabled"},
    )
    page_size = fields.Nested(
        LDAPPageSizeSelectorRequest,
        description="If the page size is enabled and its value.",
        example={"state": "enabled", "size": 1000},
        load_default={"state": "disabled"},
    )
    response_timeout = fields.Nested(
        LDAPResponseTimeoutSelectorRequest,
        description="Enable the response timeout and define its value.",
        example={"state": "enabled", "seconds": 5},
        load_default={"state": "disabled"},
    )


class LDAPConnectionCreateRequest(LDAPConnectionRequest):
    connection_suffix = fields.Nested(
        LDAPConnectionSuffixCreateSelectorRequest,
        description="If the connection suffix is enabled and what its set to.",
        example={"state": "enabled", "suffix": "suffix_example"},
        load_default={"state": "disabled"},
    )


class LDAPConnectionUpdateRequest(LDAPConnectionRequest):
    connection_suffix = fields.Nested(
        LDAPConnectionSuffixUpdateSelectorRequest,
        description="If the connection suffix is enabled and what its set to.",
        example={"state": "enabled", "suffix": "suffix_example"},
        load_default={"state": "disabled"},
    )


class LDAPUserSearchFilterRequest(LDAPCheckboxEnabledRequest):
    filter = fields.String(
        description="Using this option you can define an optional LDAP filter which is used during"
        " LDAP searches. It can be used to only handle a subset of the users below the given base DN.",
        example="(&(objectclass=user)(objectcategory=person))",
        required=True,
    )


class LDAPUserSearchFilterRequestSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPUserSearchFilterRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPUserGroupFilterRequest(LDAPCheckboxEnabledRequest):
    filter = fields.String(
        description="Define the DN of a group object which is used to filter the users.",
        example="CN=cmk-users,OU=groups,DC=example,DC=com",
        required=True,
    )


class LDAPUserGroupFilterRequestSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPUserGroupFilterRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPUserIDAttributeRequest(LDAPCheckboxEnabledRequest):
    attribute = fields.String(
        description="The attribute used to identify the individual users. It must have unique values"
        " to make an user identifyable by the value of this attribute.",
        example="attribute_example",
        required=True,
    )


class LDAPUserIDAttributeRequestSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPUserIDAttributeRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPUsersRequest(BaseSchema):
    user_base_dn = fields.String(
        description="Give a base distinguished name here. All user accounts to synchronize must be "
        "located below this one.",
        example="OU=users,DC=example,DC=com",
        load_default="",
    )
    search_scope = fields.String(
        enum=[
            "search_whole_subtree",
            "search_only_base_dn_entry",
            "search_all_one_level_below_base_dn",
        ],
        description="Scope to be used in LDAP searches. In most cases Search whole subtree below the base"
        " DN is the best choice. It searches for matching objects recursively.",
        example="search_whole_subtree",
        load_default="search_whole_subtree",
    )
    search_filter = fields.Nested(
        LDAPUserSearchFilterRequestSelector,
        description="Enable and define an optional LDAP filter.",
        example={
            "state": "enabled",
            "filter": "(&(objectclass=user)(objectcategory=person))",
        },
        load_default={"state": "disabled"},
    )
    filter_group = fields.Nested(
        LDAPUserGroupFilterRequestSelector,
        description="Enable and define the DN of a group object which is used to filter the users.",
        example={
            "state": "enabled",
            "filter": "CN=cmk-users,OU=groups,DC=example,DC=com",
        },
        load_default={"state": "disabled"},
    )
    user_id_attribute = fields.Nested(
        LDAPUserIDAttributeRequestSelector,
        description="Enable and define a user ID attribute.",
        example={"state": "enabled", "attribute": "attribute_example"},
        load_default={"state": "disabled"},
    )
    user_id_case = fields.String(
        enum=["dont_convert_to_lowercase", "convert_to_lowercase"],
        description="Convert imported User-IDs to lower case during synchronization or leave as is.",
        example="convert_to_lowercase",
        load_default="dont_convert_to_lowercase",
    )
    umlauts_in_user_ids = fields.String(
        enum=["keep_umlauts", "replace_umlauts"],
        description="Checkmk does not support special characters in User-IDs. However, to deal with LDAP"
        " users having umlauts in their User-IDs you previously had the choice to replace umlauts with "
        "other characters. This option is still available for backward compatibility, but you are advised"
        " to use the 'keep_umlauts' option for new installations.",
        example="keep_umlauts",
        load_default="keep_umlauts",
    )
    create_users = fields.String(
        enum=["on_login", "on_sync"],
        description="Create user accounts during sync or on the first login",
        example="on_sync",
        load_default="on_login",
    )


class LDAPGroupSearchFilterRequest(LDAPCheckboxEnabledRequest):
    filter = fields.String(
        description="Define an optional LDAP filter which is used during group related LDAP searches. "
        "It can be used to only handle a subset of the groups below the given group base DN.",
        example="(objectclass=group)",
        required=True,
    )


class LDAPGroupSearchFilterSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPGroupSearchFilterRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPMemberAttributeRequest(LDAPCheckboxEnabledRequest):
    attribute = fields.String(
        description="The attribute used to identify users group memberships.",
        example="example_member",
        required=True,
    )


class LDAPMemberAttributeSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPMemberAttributeRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPGroupsRequest(BaseSchema):
    group_base_dn = fields.String(
        description="Give a base distinguished name here. All groups used must be located below this one.",
        example="OU=groups,DC=example,DC=com",
        load_default="",
    )
    search_scope = fields.String(
        enum=[
            "search_whole_subtree",
            "search_only_base_dn_entry",
            "search_all_one_level_below_base_dn",
        ],
        description="Scope to be used in group related LDAP searches. In most cases Search whole subtree "
        "below the base DN is the best choice. It searches for matching objects in the given base recursively.",
        example="search_whole_subtree",
        load_default="search_whole_subtree",
    )
    search_filter = fields.Nested(
        LDAPGroupSearchFilterSelector,
        description="Enable and define an optional LDAP filter.",
        example={"state": "enabled", "filter": "(objectclass=group)"},
        load_default={"state": "disabled"},
    )
    member_attribute = fields.Nested(
        LDAPMemberAttributeSelector,
        description="Enable and define a member attribute.",
        example={"state": "enabled", "attribute": "example_member"},
        load_default={"state": "disabled"},
    )


class LDAPSyncPluginAttributeRequest(LDAPCheckboxEnabledRequest):
    attribute_to_sync = fields.String(
        description="The attribute to sync",
        required=True,
    )


class LDAPSyncPluginAttrubuteSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPSyncPluginAttributeRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPSyncPluginNestedOtherConnectionsRequest(LDAPCheckboxEnabledRequest):
    handle_nested = fields.Boolean(
        description="Once you enable this option, this plug-in will not only handle direct group"
        " memberships, instead it will also dig into nested groups and treat the members of those"
        " groups as contact group members as well. Please bear in mind that this feature might increase "
        "the execution time of your LDAP sync.",
        example=True,
        load_default=False,
    )
    sync_from_other_connections = fields.List(
        LDAPConnectionID(presence="should_exist"),
        description="The LDAP attribute whose contents shall be synced into this custom attribute.",
        example=["LDAP_1", "LDAP_2"],
        load_default=[],
    )


class LDAPSyncPluginGroupsToContactGroupsSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPSyncPluginNestedOtherConnectionsRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPCheckboxCustomTimeRangeEnabledRequest(LDAPCheckboxEnabledRequest):
    from_time = Timestamp(
        description="The start of the time range",
        required=True,
        example="2024-02-29T17:32:28+00:00",
    )
    to_time = Timestamp(
        description="The end of the time range",
        required=True,
        example="2024-03-04T12:12:56+00:00",
    )


class LDAPCustomTimeRangeSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPCheckboxCustomTimeRangeEnabledRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPSyncPluginGroupsValueRequest(BaseSchema):
    temporarily_disable_all_notifications = fields.Boolean(
        description="When this option is active you will not get any alerts or other "
        "notifications via email, SMS or similar. This overrides all other notification "
        "settings and rules, so make sure that you know what you're doing. Moreover you "
        "can specify a time range where no notifications are generated.",
        load_default=False,
    )
    custom_time_range = fields.Nested(
        LDAPCustomTimeRangeSelector,
        description="",
        required=True,
        example={
            "from_time": "2024-02-29T17:32:28+00:00",
            "to_time": "2024-03-04T12:12:56+00:00",
        },
    )


class LDAPSyncPluginGroupBaseRequest(BaseSchema):
    group_cn = fields.String(
        description="The common name of the group",
        required=True,
        example="a_group_cn",
    )
    attribute_to_set = fields.String(
        description="The attribute to set",
        required=True,
        example="disable_notifications",
    )


class LDAPSyncPluginGroupDisableNotificationsRequest(LDAPSyncPluginGroupBaseRequest):
    value = fields.Nested(
        LDAPSyncPluginGroupsValueRequest,
        description="The value to set",
        required=True,
    )


class LDAPSyncPluginGroupStartURLRequest(LDAPSyncPluginGroupBaseRequest):
    value = fields.String(
        description="The URL that the user should be redirected to after login. There is a "
        "'default_start_url', a 'welcome_page', and any other will be treated as a custom URL",
        required=True,
        example="welcome_page",
    )


class LDAPSyncPluginGroupAllOthersRequest(LDAPSyncPluginGroupBaseRequest):
    value = fields.String(
        description="",
        required=True,
        example="per_entry",
    )


class LDAPSyncPluginGroupsToSyncSelector(OneOfSchema):
    type_field = "attribute_to_set"
    type_field_remove = False
    type_schemas = {
        "disable_notifications": LDAPSyncPluginGroupDisableNotificationsRequest,
        "start_url": LDAPSyncPluginGroupStartURLRequest,
        "all_others": LDAPSyncPluginGroupAllOthersRequest,
    }

    @override
    def get_data_type(self, data):
        data_type = data.get(self.type_field)
        if data_type not in ("start_url", "disable_notifications"):
            return "all_others"

        return data_type


class LDAPSyncPluginGroupsToAttributesRequest(LDAPSyncPluginNestedOtherConnectionsRequest):
    groups_to_sync = fields.Nested(
        LDAPSyncPluginGroupsToSyncSelector,
        description="",
        many=True,
        load_default=[],
    )


class LDAPSyncPluginGroupsToAttributesSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPSyncPluginGroupsToAttributesRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPRoleElementRequest(BaseSchema):
    group_dn = fields.String(
        description="This group must be defined within the scope of the LDAP Group Settings",
        example="cmk-users",
        required=True,
    )
    search_in = fields.String(
        description="An existing ldap connection. Use 'this_connection' to select the current connection ",
        example="this_connection",
        load_default="this_connection",
    )

    @post_load
    def _post_load(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        if data["search_in"] != "this_connection":
            if data["search_in"] not in get_ldap_connections():
                raise ValidationError(f"The LDAP connection {data['search_in']} does not exist.")
        return data


class LDAPEnableGroupsToRoles(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = ValueTypedDictSchema.wrap_field(
            fields.Nested(
                LDAPRoleElementRequest,
                many=True,
            )
        )

    class Meta:
        unknown = INCLUDE

    handle_nested = fields.Boolean(
        required=False,
        description="Once you enable this option, this plug-in will not only handle direct group "
        "memberships, instead it will also dig into nested groups and treat the members of those "
        "groups as contact group members as well. Please bear in mind that this feature might "
        "increase the execution time of your LDAP sync",
        load_default=False,
    )
    state = fields.Constant(
        "enabled",
        required=True,
        example="enabled",
        description="This config parameter is enabled.",
    )
    admin = fields.Nested(
        LDAPRoleElementRequest,
        many=True,
        required=False,
    )
    agent_registration = fields.Nested(
        LDAPRoleElementRequest,
        many=True,
        required=False,
    )
    guest = fields.Nested(
        LDAPRoleElementRequest,
        many=True,
        required=False,
    )
    user = fields.Nested(
        LDAPRoleElementRequest,
        many=True,
        required=False,
    )

    @pre_load
    def _pre_load(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return {k: v for k, v in data.items() if k in self.fields}


class LDAPGroupsToRolesSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPEnableGroupsToRoles,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPSyncPluginsRequest(BaseSchema):
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    @pre_load
    def _handle_menu_icons_fields(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        params = {key: value for key, value in data.items() if value is not None}
        if params:
            data["main_menu_icons"] = mutually_exclusive_fields(
                dict,
                params,
                "mega_menu_icons",
                "main_menu_icons",
                default={"state": "disabled"},
            )
        return data

    alias = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="Enables and populates the alias attribute of the Setup user by synchronizing an "
        "attribute from the LDAP user account. By default the LDAP attribute cn is used.",
        load_default={"state": "disabled"},
    )
    authentication_expiration = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="This plug-in when enabled fetches all information which is needed to check whether "
        "or not an already authenticated user should be deauthenticated, e.g. because the password has "
        "changed in LDAP or the account has been locked.",
        load_default={"state": "disabled"},
    )
    disable_notifications = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="When this option is enabled you will not get any alerts or other notifications "
        "via email, SMS or similar. This overrides all other notification settings and rules, so make"
        " sure that you know what you do. Moreover you can specify a time range where no notifications"
        " are generated.",
        load_default={"state": "disabled"},
    )
    email_address = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="Synchronizes the email of the LDAP user account into Checkmk when enabled",
        load_default={"state": "disabled"},
    )
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    mega_menu_icons = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="Deprecated - use `main_menu_icons` instead.",
        load_default={"state": "disabled"},
        deprecated=True,
    )
    main_menu_icons = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="When enabled, in the main menus you can select between two options: Have a green icon"
        " only for the headlines – the 'topics' – for lean design. Or have a colored icon for every entry"
        " so that over time you can zoom in more quickly to a specific entry.",
        load_default={"state": "disabled"},
    )
    navigation_bar_icons = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="With this option enabled you can define if icons in the navigation bar should show"
        " a title or not. This gives you the possibility to save some space in the UI.",
        load_default={"state": "disabled"},
    )
    pager = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="When enabled, this plug-in synchronizes a field of the users LDAP account to the pager"
        " attribute of the Setup user accounts, which is then forwarded to the monitoring core and can be"
        " used for notifications. By default the LDAP attribute mobile is used.",
        load_default={"state": "disabled"},
    )
    show_mode = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="In some places like e.g. the main menu Checkmk divides features, filters, input "
        "fields etc. in two categories, showing more or less entries. With this option you can set a "
        "default mode for unvisited menus. Alternatively, you can enforce to show more, so that the "
        "round button with the three dots is not shown at all.",
        load_default={"state": "disabled"},
    )
    ui_sidebar_position = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="The sidebar position",
        load_default={"state": "disabled"},
    )
    start_url = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="The start URL to display in main frame.",
        load_default={"state": "disabled"},
    )
    temperature_unit = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="Set the temperature unit used for graphs and perfometers. The default unit can "
        "be configured here. Note that this setting does not affect the temperature unit used in service"
        " outputs, which can however be configured in this ruleset.",
        load_default={"state": "disabled"},
    )
    ui_theme = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="The user interface theme",
        load_default={"state": "disabled"},
    )
    visibility_of_hosts_or_services = fields.Nested(
        LDAPSyncPluginAttrubuteSelector,
        description="When this option is checked, the status GUI will only display hosts and "
        "services that the user is a contact for - even they have the permission for seeing all objects.",
        load_default={"state": "disabled"},
    )
    contact_group_membership = fields.Nested(
        LDAPSyncPluginGroupsToContactGroupsSelector,
        description="This plug-in allows you to synchronize group memberships of the LDAP user account into"
        " the contact groups of the Checkmk user account. This allows you to use the group based permissions"
        " of your LDAP directory in Checkmk.",
        load_default={"state": "disabled"},
    )
    groups_to_custom_user_attributes = fields.Nested(
        LDAPSyncPluginGroupsToAttributesSelector,
        description="This plug-in allows you to synchronize group memberships of the LDAP user account into "
        "the custom attributes of the Checkmk user account. This allows you to use the group based permissions"
        " of your LDAP directory in Checkmk.",
        load_default={"state": "disabled"},
    )
    groups_to_roles = fields.Nested(
        LDAPGroupsToRolesSelector,
        unknown=INCLUDE,
        description="Configures the roles of the user depending on its group memberships in LDAP. "
        "Please note: Additionally the user is assigned to the Default Roles. Deactivate them if unwanted.",
        load_default={"state": "disabled"},
    )

    @post_load(pass_original=True)
    def _validate_extra_attributes(
        self,
        result_data: dict[str, Any],
        original_data: MutableMapping[str, Any],
        **_unused_args: Any,
    ) -> dict[str, Any]:
        if custom_userroles := {
            k: v
            for k, v in original_data.get("groups_to_roles", {}).items()
            if k not in LDAPEnableGroupsToRoles().fields
        }:
            roles = UserRolesConfigFile().load_for_reading()
            test_field = fields.Nested(LDAPRoleElementRequest, many=True, required=False)
            for custom_userrole, roledata in custom_userroles.items():
                if custom_userrole not in roles:
                    raise ValidationError(f"Unknown user role: {custom_userrole!r}")
                try:
                    test_field.deserialize(roledata)
                except ValidationError as e:
                    raise ValidationError(f"Invalid value for {custom_userrole!r}: {e.messages}")

                result_data["groups_to_roles"][custom_userrole] = roledata

        for field in self.fields:
            original_data.pop(field, None)

        if not original_data:
            return result_data

        custom_user_attributes = load_custom_attrs_from_mk_file(lock=False)["user"]
        test_field = fields.Nested(LDAPSyncPluginCustomSelector, required=False)

        for name, value in original_data.items():
            if name not in {attr["title"] for attr in custom_user_attributes}:
                raise ValidationError(f"Unknown custom user attribute: {name!r}")

            try:
                test_field.deserialize(value)

            except ValidationError as e:
                raise ValidationError(f"Invalid value for {name!r}: {e.messages}")

            result_data[name] = value

        return result_data


class LDAPSyncPluginCustomRequest(LDAPCheckboxEnabledRequest):
    attribute_to_sync = fields.String(
        description="The attribute to sync for a custom user attribute",
        example={"state": "enabled", "attribute_to_sync": "custom_attr_1"},
        load_default={"state": "disabled"},
    )


class LDAPSyncPluginCustomSelector(LDAPCheckboxSelector):
    type_schemas = {
        "enabled": LDAPSyncPluginCustomRequest,
        "disabled": LDAPCheckboxDisabledRequest,
    }


class LDAPSyncIntervalRequest(BaseSchema):
    days = fields.Integer(
        description="The sync interval in days",
        example=5,
        load_default=0,
    )
    hours = fields.Integer(
        description="The sync interval in hours",
        example=2,
        load_default=0,
    )
    minutes = fields.Integer(
        description="The sync interval in minutes",
        example=30,
        load_default=5,
    )


class LDAPOtherRequest(BaseSchema):
    sync_interval = fields.Nested(
        LDAPSyncIntervalRequest,
        description="This option defines the interval of the LDAP synchronization. This setting is only"
        " used by sites which have the automatic user synchronization enabled.",
        load_default={"days": 0, "hours": 0, "minutes": 5},
    )


class LDAPConnectionConfigRequest(BaseSchema):
    users = fields.Nested(
        LDAPUsersRequest,
        description="The LDAP user configuration",
        example={
            "user_base_dn": "ou=OrgUnit,dc=domaincomp,dc=de",
            "search_scope": "search_only_base_dn_entry",
            "search_filter": {
                "state": "enabled",
                "filter": "(&(objectclass=user)(objectcategory=person))",
            },
            "filter_group": {"state": "enabled", "filter": "filtergroupexample"},
            "user_id_attribute": {
                "state": "enabled",
                "attribute": "userattributeexample",
            },
            "user_id_case": "convert_to_lowercase",
            "umlauts_in_user_ids": "keep_umlauts",
            "create_users": "on_login",
        },
        load_default={
            "user_base_dn": "",
            "search_scope": "search_only_base_dn_entry",
            "search_filter": {"state": "disabled"},
            "filter_group": {"state": "disabled"},
            "user_id_attribute": {"state": "disabled"},
            "user_id_case": "dont_convert_to_lowercase",
            "umlauts_in_user_ids": "keep_umlauts",
            "create_users": "on_login",
        },
    )
    groups = fields.Nested(
        LDAPGroupsRequest,
        description="The LDAP group configuration",
        example={
            "group_base_dn": "ou=OrgUnit,dc=domaincomp,dc=de",
            "search_scope": "search_whole_subtree",
            "search_filter": {"state": "enabled", "filter": "(objectclass=group)"},
            "member_attribute": {"state": "enabled", "attribute": "member"},
        },
        load_default={
            "group_base_dn": "",
            "search_scope": "search_whole_subtree",
            "search_filter": {"state": "disabled"},
            "member_attribute": {"state": "disabled"},
        },
    )
    sync_plugins = fields.Nested(
        LDAPSyncPluginsRequest,
        unknown=INCLUDE,
        description="The LDAP sync plug-ins configuration",
        example={},
        load_default={},
    )
    other = fields.Nested(
        LDAPOtherRequest,
        description="Other config options for the LDAP connection.",
        example={"sync_interval": {"days": 0, "hours": 0, "minutes": 30}},
        load_default={"sync_interval": {"days": 0, "hours": 0, "minutes": 5}},
    )

    @post_load
    def _post_load(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        group_base_dn = data["groups"]["group_base_dn"]
        for key, grouplist in data["sync_plugins"].get("groups_to_roles", {}).items():
            if key in {"state", "handle_nested"}:
                continue
            for group in grouplist:
                if not group["group_dn"].lower().endswith(group_base_dn.lower()):
                    raise ValidationError(
                        f"The configured group_dn '{group['group_dn']}' must end with the group_base_dn '{group_base_dn}'."
                    )
        return data


GENERAL_PROPERTIES_EXAMPLE = {
    "id": "ldap_1",
    "description": "1st ldap connection",
    "comment": "test_comment",
    "documentation_url": "https://checkmk.com/doc/ldap_connections",
    "rule_activation": "activated",
}

LDAP_CONNECTION_EXAMPLE = {
    "directory_type": {
        "type": "active_directory_manual",
        "ldap_server": "123.31.12.34",
    },
    "bind_credentials": {
        "state": "enabled",
        "type": "explicit",
        "bind_dn": "cn=commonname,ou=OrgUnit,dc=domaincomp,dc=de",
        "explicit_password": "yourpass",
    },
    "tcp_port": {"state": "enabled", "port": 389},
    "ssl_encryption": "enable_ssl",
    "connect_timeout": {"state": "enabled", "seconds": 5.0},
    "ldap_version": {"state": "enabled", "version": 3},
    "page_size": {"state": "enabled", "size": 1000},
    "response_timeout": {"state": "enabled", "seconds": 60},
    "connection_suffix": {"state": "enabled", "suffix": "dc=domaincomp,dc=de"},
}


class LDAPConnectionConfigCreateRequest(LDAPConnectionConfigRequest):
    general_properties = fields.Nested(
        LDAPGeneralPropertiesCreateRequest,
        required=True,
        description="General properties of an LDAP connection.",
        example=GENERAL_PROPERTIES_EXAMPLE,
    )
    ldap_connection = fields.Nested(
        LDAPConnectionCreateRequest,
        required=True,
        description="The LDAP connection configuration",
        example=LDAP_CONNECTION_EXAMPLE,
    )


class LDAPConnectionConfigUpdateRequest(LDAPConnectionConfigRequest):
    general_properties = fields.Nested(
        LDAPGeneralPropertiesUpdateRequest,
        required=True,
        description="General properties of an LDAP connection.",
        example=GENERAL_PROPERTIES_EXAMPLE,
    )

    ldap_connection = fields.Nested(
        LDAPConnectionUpdateRequest,
        required=True,
        description="The LDAP connection configuration",
        example=LDAP_CONNECTION_EXAMPLE,
    )
