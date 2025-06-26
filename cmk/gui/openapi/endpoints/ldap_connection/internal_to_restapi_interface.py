#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast, get_args, Literal, TypedDict

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.type_defs import DisableNotificationsAttribute
from cmk.gui.userdb import (
    ACTIVE_DIR,
    ActivePlugins,
    ConfigurableUserConnectionSpec,
    CUSTOM_USER_ATTRIBUTE,
    DIR_SERVER_389,
    DISABLE_NOTIFICATIONS,
    Discover,
    Fixed,
    FORCE_AUTH_USER,
    get_ldap_connections,
    GroupsToAttributes,
    GroupsToContactGroups,
    GroupsToRoles,
    GroupsToSync,
    ICONS_PER_ITEM,
    LDAPConnectionConfigDiscover,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
    NAV_HIDE_ICONS_TITLE,
    OPEN_LDAP,
    RoleSpec,
    SHOW_MODE,
    START_URL,
    SyncAttribute,
    TEMP_UNIT,
    UI_SIDEBAR_POSITIONS,
    UI_THEME,
    UserConnectionConfigFile,
)
from cmk.gui.userdb.ldap_connector import LDAPUserConnector


class APICheckboxDisabled(TypedDict):
    state: Literal["disabled"]


class APICheckboxEnabled(TypedDict):
    state: Literal["enabled"]


class APIGeneralProperties(TypedDict):
    id: str
    description: str
    comment: str
    documentation_url: str
    rule_activation: Literal["activated", "deactivated"]


@dataclass
class GeneralProperties:
    id: str
    description: str
    comment: str
    docu_url: str
    disabled: bool

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> GeneralProperties:
        return cls(
            id=config["id"],
            description=config["description"],
            comment=config["comment"],
            docu_url=config["docu_url"],
            disabled=config["disabled"],
        )

    @classmethod
    def from_api_request(cls, config: APIGeneralProperties) -> GeneralProperties:
        return cls(
            id=config["id"],
            description=config["description"],
            comment=config["comment"],
            docu_url=config["documentation_url"],
            disabled=config["rule_activation"] == "deactivated",
        )

    def api_response(self) -> APIGeneralProperties:
        r: APIGeneralProperties = {
            "id": self.id,
            "description": self.description,
            "comment": self.comment,
            "documentation_url": self.docu_url,
            "rule_activation": "deactivated" if self.disabled else "activated",
        }
        return r


class APIDirTypeManual(TypedDict):
    type: Literal[
        "active_directory_manual",
        "open_ldap",
        "389_directory_server",
    ]
    ldap_server: str
    failover_servers: list[str]


class APIActiveDirAuto(TypedDict):
    type: Literal["active_directory_automatic"]
    domain: str


class APIBindExplicit(APICheckboxEnabled):
    type: Literal["explicit"]
    bind_dn: str
    explicit_password: str


class APIBindStore(APICheckboxEnabled):
    type: Literal["store"]
    bind_dn: str
    password_store_id: str


class APITcpPort(APICheckboxEnabled):
    port: int


class APIConnectTimeout(APICheckboxEnabled):
    seconds: float


class APILDAPVersion(APICheckboxEnabled):
    version: Literal[2, 3]


class APIPageSize(APICheckboxEnabled):
    size: int


class APIResponseTimeout(APICheckboxEnabled):
    seconds: int


class APIConnectionSuffix(APICheckboxEnabled):
    suffix: str


class APIConnectionConfig(TypedDict):
    directory_type: APIDirTypeManual | APIActiveDirAuto
    bind_credentials: APICheckboxDisabled | APIBindExplicit | APIBindStore
    tcp_port: APICheckboxDisabled | APITcpPort
    ssl_encryption: Literal["enable_ssl", "disable_ssl"]
    connect_timeout: APICheckboxDisabled | APIConnectTimeout
    ldap_version: APICheckboxDisabled | APILDAPVersion
    page_size: APICheckboxDisabled | APIPageSize
    response_timeout: APICheckboxDisabled | APIResponseTimeout
    connection_suffix: APICheckboxDisabled | APIConnectionSuffix


CHECKBOX = APICheckboxDisabled | APICheckboxEnabled


@dataclass
class ConnectionConfig:
    directory_type: DIR_SERVER_389 | OPEN_LDAP | ACTIVE_DIR
    bind: tuple[str, tuple[Literal["password", "store"], str]] | None
    port: int | None
    use_ssl: Literal[True] | None
    connect_timeout: float | None
    version: Literal[2, 3] | None
    page_size: int | None
    response_timeout: int | None
    suffix: str | None

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> ConnectionConfig:
        return cls(
            directory_type=config["directory_type"],
            bind=config.get("bind"),
            port=config.get("port"),
            use_ssl=config.get("use_ssl"),
            connect_timeout=config.get("connect_timeout"),
            version=config.get("version"),
            page_size=config.get("page_size"),
            response_timeout=config.get("response_timeout"),
            suffix=config.get("suffix"),
        )

    @classmethod
    def from_api_request(cls, config: APIConnectionConfig) -> ConnectionConfig:
        api_dir_type = config["directory_type"]

        dir_type: ACTIVE_DIR | OPEN_LDAP | DIR_SERVER_389

        if api_dir_type["type"] == "active_directory_automatic":
            ad_discover = LDAPConnectionConfigDiscover(
                connect_to=("discover", Discover(domain=api_dir_type["domain"]))
            )
            dir_type = ("ad", ad_discover)

        else:
            fixed = Fixed(server=api_dir_type["ldap_server"])
            if failover_servers := api_dir_type.get("failover_servers"):
                fixed["failover_servers"] = failover_servers

            fixed_connection = LDAPConnectionConfigFixed(connect_to=("fixed_list", fixed))

            if api_dir_type["type"] == "active_directory_manual":
                dir_type = ("ad", fixed_connection)

            elif api_dir_type["type"] == "open_ldap":
                dir_type = ("openldap", fixed_connection)

            else:
                dir_type = ("389directoryserver", fixed_connection)

        bind_credentials: tuple[str, tuple[Literal["password", "store"], str]] | None
        if config["bind_credentials"]["state"] == "enabled":
            if config["bind_credentials"]["type"] == "explicit":
                explicit: APIBindExplicit = config["bind_credentials"]
                bind_credentials = (
                    explicit["bind_dn"],
                    ("password", explicit["explicit_password"]),
                )
            else:
                store: APIBindStore = config["bind_credentials"]
                bind_credentials = (
                    store["bind_dn"],
                    ("store", store["password_store_id"]),
                )
        else:
            bind_credentials = None

        port = config["tcp_port"]["port"] if config["tcp_port"]["state"] == "enabled" else None
        connect_timeout = (
            config["connect_timeout"]["seconds"]
            if config["connect_timeout"]["state"] == "enabled"
            else None
        )
        version = (
            config["ldap_version"]["version"]
            if config["ldap_version"]["state"] == "enabled"
            else None
        )
        page_size = (
            config["page_size"]["size"] if config["page_size"]["state"] == "enabled" else None
        )
        response_timeout = (
            config["response_timeout"]["seconds"]
            if config["response_timeout"]["state"] == "enabled"
            else None
        )
        suffix = (
            config["connection_suffix"]["suffix"]
            if config["connection_suffix"]["state"] == "enabled"
            else None
        )

        return cls(
            directory_type=dir_type,
            bind=bind_credentials,
            port=port,
            use_ssl=True if config["ssl_encryption"] == "enable_ssl" else None,
            connect_timeout=connect_timeout,
            version=version,
            page_size=page_size,
            response_timeout=response_timeout,
            suffix=suffix,
        )

    def api_response(self) -> APIConnectionConfig:
        dir_type_map: dict[
            Literal["ad", "openldap", "389directoryserver"],
            Literal["active_directory_manual", "open_ldap", "389_directory_server"],
        ] = {
            "ad": "active_directory_manual",
            "openldap": "open_ldap",
            "389directoryserver": "389_directory_server",
        }

        connect_to = self.directory_type[1]["connect_to"]
        directory_type: APIDirTypeManual | APIActiveDirAuto
        if connect_to[0] == "discover":
            directory_type = {
                "type": "active_directory_automatic",
                "domain": connect_to[1]["domain"],
            }
        else:
            directory_type = {
                "type": dir_type_map[self.directory_type[0]],
                "ldap_server": connect_to[1]["server"],
                "failover_servers": connect_to[1].get("failover_servers", []),
            }

        bind_credentials: APICheckboxDisabled | APIBindExplicit | APIBindStore
        if self.bind is not None:
            if self.bind[1][0] == "password":
                bind_credentials = {
                    "state": "enabled",
                    "bind_dn": self.bind[0],
                    "type": "explicit",
                    "explicit_password": self.bind[1][1],
                }
            else:
                bind_credentials = {
                    "state": "enabled",
                    "bind_dn": self.bind[0],
                    "type": "store",
                    "password_store_id": self.bind[1][1],
                }
        else:
            bind_credentials = {"state": "disabled"}

        def checkbox_state(value: str | int | float | None, schema_key: str) -> Any:
            if value is None:
                return {"state": "disabled"}
            return {"state": "enabled", schema_key: value}

        r: APIConnectionConfig = {
            "directory_type": directory_type,
            "bind_credentials": bind_credentials,
            "tcp_port": checkbox_state(self.port, "port"),
            "ssl_encryption": "enable_ssl" if self.use_ssl else "disable_ssl",
            "connect_timeout": checkbox_state(self.connect_timeout, "seconds"),
            "ldap_version": checkbox_state(self.version, "version"),
            "page_size": checkbox_state(self.page_size, "size"),
            "response_timeout": checkbox_state(self.response_timeout, "seconds"),
            "connection_suffix": checkbox_state(self.suffix, "suffix"),
        }
        return r


SEARCH_SCOPE_INT = Literal[
    "sub",
    "base",
    "one",
]
SEARCH_SCOPE_API = Literal[
    "search_whole_subtree",
    "search_only_base_dn_entry",
    "search_all_one_level_below_base_dn",
]

SCOPE_API_TO_INT = dict(zip(get_args(SEARCH_SCOPE_API), get_args(SEARCH_SCOPE_INT)))
SCOPE_INT_TO_API = dict(zip(get_args(SEARCH_SCOPE_INT), get_args(SEARCH_SCOPE_API)))


class APIUserSearchFilter(APICheckboxEnabled):
    filter: str


class APIUserFilterGroup(APICheckboxEnabled):
    filter: str


class APIUserAttribute(APICheckboxEnabled):
    attribute: str


class APIUsers(TypedDict):
    user_base_dn: str
    search_scope: SEARCH_SCOPE_API
    search_filter: APICheckboxDisabled | APIUserSearchFilter
    filter_group: APICheckboxDisabled | APIUserFilterGroup
    user_id_attribute: APICheckboxDisabled | APIUserAttribute
    user_id_case: Literal["dont_convert_to_lowercase", "convert_to_lowercase"]
    umlauts_in_user_ids: Literal["keep_umlauts", "replace_umlauts"]
    create_users: Literal["on_login", "on_sync"]


@dataclass
class Users:
    user_dn: str
    user_scope: SEARCH_SCOPE_INT
    user_id_umlauts: Literal["keep", "replace"]
    user_filter: str | None
    user_filter_group: str | None
    user_id: str | None
    lower_user_ids: Literal[True] | None
    create_only_on_login: Literal[True] | None

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> Users:
        return cls(
            user_dn=config["user_dn"],
            user_scope=config["user_scope"],
            user_id_umlauts=config["user_id_umlauts"],
            user_filter=config.get("user_filter"),
            user_filter_group=config.get("user_filter_group"),
            user_id=config.get("user_id"),
            lower_user_ids=config.get("lower_user_ids"),
            create_only_on_login=config.get("create_only_on_login"),
        )

    @classmethod
    def from_api_request(cls, config: APIUsers) -> Users:
        return cls(
            user_dn=config["user_base_dn"],
            user_scope=SCOPE_API_TO_INT[config["search_scope"]],
            user_id_umlauts=(
                "keep" if config["umlauts_in_user_ids"] == "keep_umlauts" else "replace"
            ),
            user_filter=(
                config["search_filter"]["filter"]
                if config["search_filter"]["state"] == "enabled"
                else None
            ),
            user_filter_group=(
                config["filter_group"]["filter"]
                if config["filter_group"]["state"] == "enabled"
                else None
            ),
            user_id=(
                config["user_id_attribute"]["attribute"]
                if config["user_id_attribute"]["state"] == "enabled"
                else None
            ),
            lower_user_ids=(True if config["user_id_case"] == "convert_to_lowercase" else None),
            create_only_on_login=True if config["create_users"] == "on_login" else None,
        )

    def api_response(self) -> APIUsers:
        def checkbox_state(value: str | None, schema_key: str) -> Any:
            if value is None:
                return {"state": "disabled"}
            return {"state": "enabled", schema_key: value}

        r: APIUsers = {
            "user_base_dn": self.user_dn,
            "search_scope": SCOPE_INT_TO_API[self.user_scope],
            "search_filter": checkbox_state(self.user_filter, "filter"),
            "filter_group": checkbox_state(self.user_filter_group, "filter"),
            "user_id_attribute": checkbox_state(self.user_id, "attribute"),
            "user_id_case": (
                "dont_convert_to_lowercase"
                if self.lower_user_ids is None
                else "convert_to_lowercase"
            ),
            "umlauts_in_user_ids": (
                "keep_umlauts" if self.user_id_umlauts == "keep" else "replace_umlauts"
            ),
            "create_users": ("on_sync" if self.create_only_on_login is None else "on_login"),
        }
        return r


class APIGroupFilter(APICheckboxEnabled):
    filter: str


class APIGroupMemberAttribute(APICheckboxEnabled):
    attribute: str


class APIGroups(TypedDict):
    group_base_dn: str
    search_scope: SEARCH_SCOPE_API
    search_filter: APICheckboxDisabled | APIGroupFilter
    member_attribute: APICheckboxDisabled | APIGroupMemberAttribute


@dataclass
class Groups:
    group_dn: str
    group_scope: SEARCH_SCOPE_INT
    group_filter: str | None = None
    group_member: str | None = None

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> Groups:
        return cls(
            group_dn=config["group_dn"],
            group_scope=config["group_scope"],
            group_filter=config.get("group_filter"),
            group_member=config.get("group_member"),
        )

    @classmethod
    def from_api_request(cls, config: APIGroups) -> Groups:
        return cls(
            group_dn=config["group_base_dn"],
            group_scope=SCOPE_API_TO_INT[config["search_scope"]],
            group_filter=(
                config["search_filter"]["filter"]
                if config["search_filter"]["state"] == "enabled"
                else None
            ),
            group_member=(
                config["member_attribute"]["attribute"]
                if config["member_attribute"]["state"] == "enabled"
                else None
            ),
        )

    def api_response(self) -> APIGroups:
        def checkbox_state(value: str | None, schema_key: str) -> Any:
            if value is None:
                return {"state": "disabled"}
            return {"state": "enabled", schema_key: value}

        search_filter: APICheckboxDisabled | APIGroupFilter = checkbox_state(
            self.group_filter, "filter"
        )
        member_attribute: APICheckboxDisabled | APIGroupMemberAttribute = checkbox_state(
            self.group_member, "attribute"
        )

        r: APIGroups = {
            "group_base_dn": self.group_dn,
            "search_scope": SCOPE_INT_TO_API[self.group_scope],
            "search_filter": search_filter,
            "member_attribute": member_attribute,
        }
        return r


class APISyncAttribute(APICheckboxEnabled):
    attribute_to_sync: str


SYNC_ATTRIBUTE = APICheckboxDisabled | APISyncAttribute


class APIContactGroupOtherConnections(APICheckboxEnabled):
    connections: list[str]


class APIContactGroupMembership(APICheckboxEnabled):
    handle_nested: bool
    sync_from_other_connections: list[str]


class APICustomTimeRange(APICheckboxEnabled):
    from_time: float
    to_time: float


API_GROUP_ATTRIBUTE_NAME = Literal[
    "disable_notifications",
    "main_menu_icons",
    "navigation_bar_icons",
    "show_mode",
    "ui_sidebar_position",
    "start_url",
    "temperature_unit",
    "ui_theme",
    "visibility_of_hosts_or_services",
]


class APIDisableNotificationsValue(TypedDict):
    temporarily_disable_all_notifications: bool
    custom_time_range: APICustomTimeRange | APICheckboxDisabled


class APIDisableNotifications(TypedDict):
    group_cn: str
    attribute_to_set: Literal["disable_notifications"]
    value: APIDisableNotificationsValue


class APIMainMenuIcons(TypedDict):
    group_cn: str
    attribute_to_set: Literal["main_menu_icons"]
    value: Literal["per_topic", "per_entry"]


class APINavBarIcons(TypedDict):
    group_cn: str
    attribute_to_set: Literal["navigation_bar_icons"]
    value: Literal[
        "show_title",
        "do_not_show_title",
    ]


class APIShowMore(TypedDict):
    group_cn: str
    attribute_to_set: Literal["show_mode"]
    value: Literal[
        "use_default_show_mode",
        "default_show_less",
        "default_show_more",
        "enforce_show_more",
    ]


class APIUISideBarPosition(TypedDict):
    group_cn: str
    attribute_to_set: Literal["ui_sidebar_position"]
    value: Literal[
        "left",
        "right",
    ]


class APIUIStartUrl(TypedDict):
    group_cn: str
    attribute_to_set: Literal["start_url"]
    value: Literal["default_start_url"] | Literal["welcome_page"] | str


class APITempUnit(TypedDict):
    group_cn: str
    attribute_to_set: Literal["temperature_unit"]
    value: Literal[
        "default_temp_unit",
        "celsius",
        "fahrenheit",
    ]


class APIUITheme(TypedDict):
    group_cn: str
    attribute_to_set: Literal["ui_theme"]
    value: Literal[
        "default_theme",
        "light",
        "dark",
    ]


class APIVisibilityOfHostService(TypedDict):
    group_cn: str
    attribute_to_set: Literal["visibility_of_hosts_or_services"]
    value: Literal[
        "show_all",
        "show_for_user_contacts_only",
    ]


class APICustom(TypedDict):
    group_cn: str
    attribute_to_set: str
    value: str


GROUPS_TO_SYNC_VALUE = (
    APIDisableNotifications
    | APIMainMenuIcons
    | APINavBarIcons
    | APIShowMore
    | APIUISideBarPosition
    | APIUIStartUrl
    | APITempUnit
    | APIUITheme
    | APIVisibilityOfHostService
    | APICustom
)


class APIGroupsToAttributes(APICheckboxEnabled):
    handle_nested: bool
    sync_from_other_connections: list[str]
    groups_to_sync: list[GROUPS_TO_SYNC_VALUE]


class APIGroupsWithConnectionID(TypedDict):
    group_dn: str
    search_in: Literal["this_connection"] | str


class APIGroupsToRoles(APICheckboxEnabled, total=False):
    handle_nested: bool
    admin: list[APIGroupsWithConnectionID]
    agent_registration: list[APIGroupsWithConnectionID]
    guest: list[APIGroupsWithConnectionID]
    user: list[APIGroupsWithConnectionID]


class APISyncPlugins(TypedDict, total=False):
    alias: SYNC_ATTRIBUTE
    authentication_expiration: SYNC_ATTRIBUTE
    disable_notifications: SYNC_ATTRIBUTE
    email_address: SYNC_ATTRIBUTE
    main_menu_icons: SYNC_ATTRIBUTE
    navigation_bar_icons: SYNC_ATTRIBUTE
    pager: SYNC_ATTRIBUTE
    show_mode: SYNC_ATTRIBUTE
    ui_sidebar_position: SYNC_ATTRIBUTE
    start_url: SYNC_ATTRIBUTE
    temperature_unit: SYNC_ATTRIBUTE
    ui_theme: SYNC_ATTRIBUTE
    visibility_of_hosts_or_services: SYNC_ATTRIBUTE
    contact_group_membership: APIContactGroupMembership | APICheckboxDisabled
    groups_to_custom_user_attributes: APIGroupsToAttributes | APICheckboxDisabled
    groups_to_roles: APIGroupsToRoles | APICheckboxDisabled


def groups_to_attributes_internal_to_api(
    groups_to_sync: list[GroupsToSync],
) -> list[GROUPS_TO_SYNC_VALUE]:
    api_groups: list[GROUPS_TO_SYNC_VALUE] = []
    value: APIDisableNotificationsValue | str
    for group in groups_to_sync:
        match group["attribute"][0]:
            case "disable_notifications":
                dn = cast(DISABLE_NOTIFICATIONS, group["attribute"])
                value = {
                    "temporarily_disable_all_notifications": dn[1].get("disable", False),
                    "custom_time_range": {"state": "disabled"},
                }

                if (timerange := dn[1].get("timerange")) is not None:
                    value["custom_time_range"] = {
                        "state": "enabled",
                        "from_time": timerange[0],
                        "to_time": timerange[1],
                    }

                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": dn[0],
                        "value": value,
                    }
                )

            case "icons_per_item":
                ii = cast(ICONS_PER_ITEM, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": "main_menu_icons",
                        "value": "per_entry" if ii[1] == "entry" else "per_topic",
                    }
                )

            case "nav_hide_icons_title":
                nh = cast(NAV_HIDE_ICONS_TITLE, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": "navigation_bar_icons",
                        "value": ("do_not_show_title" if nh[1] == "hide" else "show_title"),
                    }
                )

            case "show_mode":
                sm = cast(SHOW_MODE, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": sm[0],
                        "value": "use_default_show_mode" if sm[1] is None else sm[1],
                    }
                )

            case "ui_sidebar_position":
                ui = cast(UI_SIDEBAR_POSITIONS, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": ui[0],
                        "value": "right" if ui[1] is None else "left",
                    }
                )

            case "start_url":
                su = cast(START_URL, group["attribute"])
                match su[1]:
                    case "welcome.py":
                        value = "welcome_page"
                    case str():
                        value = su[1]
                    case _:
                        value = "default_start_url"

                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": su[0],
                        "value": value,
                    }
                )

            case "temperature_unit":
                tu = cast(TEMP_UNIT, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": tu[0],
                        "value": "default" if tu[1] is None else tu[1],
                    }
                )

            case "ui_theme":
                uit = cast(UI_THEME, group["attribute"])
                themes = {"facelift": "light", "modern-dark": "dark"}
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": uit[0],
                        "value": "default_theme" if uit[1] is None else themes[uit[1]],
                    }
                )

            case "force_authuser":
                fa = cast(FORCE_AUTH_USER, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": "visibility_of_hosts_or_services",
                        "value": ("show_all" if fa[1] is None else "show_for_user_contacts_only"),
                    }
                )

            case _:
                cua = cast(CUSTOM_USER_ATTRIBUTE, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": cua[0],
                        "value": cua[1],
                    }
                )
    return api_groups


def sync_attribute_to_internal(
    api_field: SYNC_ATTRIBUTE | None,
) -> None | SyncAttribute:
    if api_field is None:
        return None

    if api_field["state"] == "enabled":
        return {"attr": api_field["attribute_to_sync"]}
    return None


def contact_group_membership_req_to_int(
    data: APIContactGroupMembership | APICheckboxDisabled | None,
) -> None | GroupsToContactGroups:
    if data is None:
        return None

    if data["state"] == "disabled":
        return None

    groups_to_cg: GroupsToContactGroups = {"other_connections": data["sync_from_other_connections"]}
    if data.get("handle_nested"):
        groups_to_cg["nested"] = True

    return groups_to_cg


def groups_to_attributes_api_to_int(
    data: APIGroupsToAttributes | APICheckboxDisabled | None,
) -> None | GroupsToAttributes:
    if data is None:
        return None

    if data["state"] == "disabled":
        return None

    groups_to_attributes: GroupsToAttributes = {
        "other_connections": data["sync_from_other_connections"],
        "groups": [],
    }

    if data.get("handle_nested"):
        groups_to_attributes["nested"] = True

    for group in data["groups_to_sync"]:
        groups_to_sync: GroupsToSync

        if group["attribute_to_set"] == "disable_notifications":
            dn_value_api = cast(APIDisableNotificationsValue, group["value"])
            v_int: DisableNotificationsAttribute = {}

            if dn_value_api["temporarily_disable_all_notifications"]:
                v_int["disable"] = True

            if dn_value_api["custom_time_range"]["state"] == "enabled":
                timeranges: APICustomTimeRange = dn_value_api["custom_time_range"]
                v_int["timerange"] = (timeranges["from_time"], timeranges["to_time"])

            disable_notifications: DISABLE_NOTIFICATIONS = (
                "disable_notifications",
                v_int,
            )

            groups_to_sync = {
                "cn": group["group_cn"],
                "attribute": disable_notifications,
            }

        else:
            match group["attribute_to_set"]:
                case "main_menu_icons":
                    main_menu_icons = cast(APIMainMenuIcons, group)
                    groups_to_sync = {
                        "cn": main_menu_icons["group_cn"],
                        "attribute": (
                            "icons_per_item",
                            None if main_menu_icons["value"] == "per_topic" else "entry",
                        ),
                    }

                case "navigation_bar_icons":
                    navbaricons = cast(APINavBarIcons, group)
                    groups_to_sync = {
                        "cn": navbaricons["group_cn"],
                        "attribute": (
                            "nav_hide_icons_title",
                            ("hide" if navbaricons["value"] == "do_not_show_title" else None),
                        ),
                    }

                case "show_mode":
                    show_mode = cast(APIShowMore, group)
                    groups_to_sync = {
                        "cn": show_mode["group_cn"],
                        "attribute": (
                            "show_mode",
                            (
                                None
                                if show_mode["value"] == "use_default_show_mode"
                                else show_mode["value"]
                            ),
                        ),
                    }

                case "ui_sidebar_position":
                    sidebar_pos_group = cast(APIUISideBarPosition, group)
                    sidebar_pos_attribute: UI_SIDEBAR_POSITIONS = (
                        "ui_sidebar_position",
                        None if sidebar_pos_group["value"] == "right" else "left",
                    )
                    groups_to_sync = {
                        "cn": sidebar_pos_group["group_cn"],
                        "attribute": sidebar_pos_attribute,
                    }

                case "start_url":
                    starturl = cast(APIUIStartUrl, group)
                    value: str | None
                    match start_url := starturl["value"]:
                        case "welcome_page":
                            value = "welcome.py"
                        case "default_start_url":
                            value = None
                        case _:
                            value = start_url

                    groups_to_sync = {
                        "cn": starturl["group_cn"],
                        "attribute": ("start_url", value),
                    }

                case "temperature_unit":
                    tempunit = cast(APITempUnit, group)
                    groups_to_sync = {
                        "cn": tempunit["group_cn"],
                        "attribute": (
                            "temperature_unit",
                            (
                                None
                                if tempunit["value"] == "default_temp_unit"
                                else tempunit["value"]
                            ),
                        ),
                    }

                case "ui_theme":
                    uithemegroup = cast(APIUITheme, group)
                    theme_map: dict[str, Literal["facelift", "modern-dark"] | None] = {
                        "default_theme": None,
                        "light": "facelift",
                        "dark": "modern-dark",
                    }
                    ui_theme_attribute: UI_THEME = (
                        "ui_theme",
                        theme_map[uithemegroup["value"]],
                    )
                    groups_to_sync = {
                        "cn": uithemegroup["group_cn"],
                        "attribute": ui_theme_attribute,
                    }

                case "visibility_of_hosts_or_services":
                    forceauth = cast(APIVisibilityOfHostService, group)
                    groups_to_sync = {
                        "cn": forceauth["group_cn"],
                        "attribute": (
                            "force_authuser",
                            forceauth["value"] == "show_for_user_contacts_only",
                        ),
                    }

                case _:
                    custom = cast(APICustom, group)
                    attribute: CUSTOM_USER_ATTRIBUTE = (
                        custom["attribute_to_set"],
                        custom["value"],
                    )
                    groups_to_sync = {"cn": custom["group_cn"], "attribute": attribute}

        groups_to_attributes["groups"].append(groups_to_sync)

    return groups_to_attributes


def groups_to_roles_req_to_int(
    data: APIGroupsToRoles | APICheckboxDisabled | None,
) -> None | GroupsToRoles:
    if data is None:
        return None

    if data["state"] == "disabled":
        return None

    groups_to_roles: GroupsToRoles = {}

    for role, groups in {k: v for k, v in data.items() if isinstance(v, list)}.items():
        groups_to_roles[role] = [  # type: ignore[literal-required]
            (
                group["group_dn"],
                None if group["search_in"] == "this_connection" else group["search_in"],
            )
            for group in groups
        ]

    if "handle_nested" in data and data["handle_nested"]:
        groups_to_roles["nested"] = True

    return groups_to_roles


@dataclass
class SyncPlugins:
    active_plugins: ActivePlugins

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> SyncPlugins:
        return cls(active_plugins=config["active_plugins"])

    @classmethod
    def from_api_request(cls, config: APISyncPlugins) -> SyncPlugins:
        ap: dict[str, Any] = {}
        ap["alias"] = sync_attribute_to_internal(config.pop("alias", None))
        ap["auth_expire"] = sync_attribute_to_internal(
            config.pop("authentication_expiration", None)
        )
        ap["disable_notifications"] = sync_attribute_to_internal(
            config.pop("disable_notifications", None)
        )
        ap["email"] = sync_attribute_to_internal(config.pop("email_address", None))
        ap["icons_per_item"] = sync_attribute_to_internal(config.pop("main_menu_icons", None))
        ap["nav_hide_icons_title"] = sync_attribute_to_internal(
            config.pop("navigation_bar_icons", None)
        )
        ap["pager"] = sync_attribute_to_internal(config.pop("pager", None))
        ap["show_mode"] = sync_attribute_to_internal(config.pop("show_mode", None))
        ap["ui_sidebar_position"] = sync_attribute_to_internal(
            config.pop("ui_sidebar_position", None)
        )
        ap["start_url"] = sync_attribute_to_internal(config.pop("start_url", None))
        ap["temperature_unit"] = sync_attribute_to_internal(config.pop("temperature_unit", None))
        ap["ui_theme"] = sync_attribute_to_internal(config.pop("ui_theme", None))
        ap["force_authuser"] = sync_attribute_to_internal(
            config.pop("visibility_of_hosts_or_services", None)
        )
        ap["groups_to_contactgroups"] = contact_group_membership_req_to_int(
            config.pop("contact_group_membership", None)
        )
        ap["groups_to_attributes"] = groups_to_attributes_api_to_int(
            config.pop("groups_to_custom_user_attributes", None)
        )
        ap["groups_to_roles"] = groups_to_roles_req_to_int(config.pop("groups_to_roles", None))

        # Custom user attributes can be added here too.
        for k, v in config.items():
            if k not in ap:
                ap[k] = sync_attribute_to_internal[v]  # type: ignore[valid-type,misc]

        active_plugins = cast(ActivePlugins, {k: v for k, v in ap.items() if v is not None})
        return cls(active_plugins=active_plugins)

    def api_response(self) -> APISyncPlugins:
        def checkbox_state(plugin_key: str) -> SYNC_ATTRIBUTE:
            value = cast(dict, self.active_plugins.get(plugin_key))
            if value is not None:
                if (attr := value.get("attr")) is not None:
                    return {"state": "enabled", "attribute_to_sync": attr}
            return {"state": "disabled"}

        r: APISyncPlugins = {
            "alias": checkbox_state("alias"),
            "authentication_expiration": checkbox_state("auth_expire"),
            "disable_notifications": checkbox_state("disable_notifications"),
            "email_address": checkbox_state("email"),
            "main_menu_icons": checkbox_state("icons_per_item"),
            "navigation_bar_icons": checkbox_state("nav_hide_icons_title"),
            "pager": checkbox_state("pager"),
            "show_mode": checkbox_state("show_mode"),
            "ui_sidebar_position": checkbox_state("ui_sidebar_position"),
            "start_url": checkbox_state("start_url"),
            "temperature_unit": checkbox_state("temperature_unit"),
            "ui_theme": checkbox_state("ui_theme"),
            "visibility_of_hosts_or_services": checkbox_state("force_authuser"),
            "contact_group_membership": {"state": "disabled"},
            "groups_to_custom_user_attributes": {"state": "disabled"},
            "groups_to_roles": {"state": "disabled"},
        }

        if (
            internal_cg_membership := self.active_plugins.get("groups_to_contactgroups")
        ) is not None:
            r["contact_group_membership"] = {
                "state": "enabled",
                "handle_nested": internal_cg_membership.get("nested", False),
                "sync_from_other_connections": internal_cg_membership.get("other_connections", []),
            }

        if internal_groups_to_attributes := self.active_plugins.get("groups_to_attributes"):
            groups_to_custom_user_attributes: APIGroupsToAttributes = {
                "state": "enabled",
                "handle_nested": internal_groups_to_attributes.get("nested", False),
                "sync_from_other_connections": internal_groups_to_attributes.get(
                    "other_connections", []
                ),
                "groups_to_sync": groups_to_attributes_internal_to_api(
                    internal_groups_to_attributes.get("groups", [])
                ),
            }
            r["groups_to_custom_user_attributes"] = groups_to_custom_user_attributes

        if internal_groups_to_roles := self.active_plugins.get("groups_to_roles"):
            groups_to_roles: APIGroupsToRoles = {"state": "enabled"}
            for k, v in internal_groups_to_roles.items():
                if k == "nested":
                    if v is True:
                        groups_to_roles["handle_nested"] = True
                    continue

                rolespec_collection = cast(list[RoleSpec], v)
                groups_to_roles[k] = [  # type: ignore[literal-required]
                    {
                        "group_dn": groupdn,
                        "search_in": (search_in if search_in is not None else "this_connection"),
                    }
                    for groupdn, search_in in rolespec_collection
                ]

            r["groups_to_roles"] = groups_to_roles

        # Custom user attributes
        for k in self.active_plugins:
            if k not in r:
                r[k] = checkbox_state(k)  # type: ignore[literal-required]

        return r


class APISyncInterval(TypedDict):
    days: int
    hours: int
    minutes: int


class APIOther(TypedDict):
    sync_interval: APISyncInterval


@dataclass
class Other:
    cache_livetime: int

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> Other:
        return cls(cache_livetime=config["cache_livetime"])

    @classmethod
    def from_api_request(cls, config: APIOther) -> Other:
        days_to_seconds = config["sync_interval"]["days"] * 86400
        hours_to_seconds = config["sync_interval"]["hours"] * 3600
        minutes_to_seconds = config["sync_interval"]["minutes"] * 60
        return cls(cache_livetime=days_to_seconds + hours_to_seconds + minutes_to_seconds)

    def api_response(self) -> APIOther:
        days, leftover_seconds = divmod(self.cache_livetime, 86400)
        hours, leftover_seconds2 = divmod(leftover_seconds, 3600)
        minutes, _ = divmod(leftover_seconds2, 60)

        r: APIOther = {
            "sync_interval": {
                "hours": hours,
                "minutes": minutes,
                "days": days,
            },
        }
        return r


class APIConnection(TypedDict):
    general_properties: APIGeneralProperties
    ldap_connection: APIConnectionConfig
    users: APIUsers
    groups: APIGroups
    sync_plugins: APISyncPlugins
    other: APIOther


@dataclass
class LDAPConnectionInterface:
    general_properties: GeneralProperties
    connection_config: ConnectionConfig
    users: Users
    groups: Groups
    sync_plugins: SyncPlugins
    other: Other

    @classmethod
    def from_mk_file_format(cls, config: LDAPUserConnectionConfig) -> LDAPConnectionInterface:
        return cls(
            general_properties=GeneralProperties.from_mk_file_format(config),
            connection_config=ConnectionConfig.from_mk_file_format(config),
            users=Users.from_mk_file_format(config),
            groups=Groups.from_mk_file_format(config),
            sync_plugins=SyncPlugins.from_mk_file_format(config),
            other=Other.from_mk_file_format(config),
        )

    @classmethod
    def from_api_request(cls, config: APIConnection) -> LDAPConnectionInterface:
        return cls(
            general_properties=GeneralProperties.from_api_request(config["general_properties"]),
            connection_config=ConnectionConfig.from_api_request(config["ldap_connection"]),
            users=Users.from_api_request(config["users"]),
            groups=Groups.from_api_request(config["groups"]),
            sync_plugins=SyncPlugins.from_api_request(config["sync_plugins"]),
            other=Other.from_api_request(config["other"]),
        )

    def api_response(self) -> dict:
        r = {
            "general_properties": self.general_properties.api_response(),
            "ldap_connection": self.connection_config.api_response(),
            "users": self.users.api_response(),
            "groups": self.groups.api_response(),
            "sync_plugins": self.sync_plugins.api_response(),
            "other": self.other.api_response(),
        }
        return r

    def to_mk_format(self) -> LDAPUserConnectionConfig:
        r: dict[str, Any] = {
            "id": self.general_properties.id,
            "description": self.general_properties.description,
            "comment": self.general_properties.comment,
            "docu_url": self.general_properties.docu_url,
            "disabled": self.general_properties.disabled,
            "directory_type": self.connection_config.directory_type,
            "user_dn": self.users.user_dn,
            "user_scope": self.users.user_scope,
            "user_id_umlauts": self.users.user_id_umlauts,
            "group_dn": self.groups.group_dn,
            "group_scope": self.groups.group_scope,
            "active_plugins": self.sync_plugins.active_plugins,
            "cache_livetime": self.other.cache_livetime,
            "type": "ldap",
            "version": self.connection_config.version,
            "page_size": self.connection_config.page_size,
            "response_timeout": self.connection_config.response_timeout,
            "suffix": self.connection_config.suffix,
            "group_filter": self.groups.group_filter,
            "group_member": self.groups.group_member,
            "bind": self.connection_config.bind,
            "port": self.connection_config.port,
            "use_ssl": self.connection_config.use_ssl,
            "connect_timeout": self.connection_config.connect_timeout,
            "user_filter": self.users.user_filter,
            "user_filter_group": self.users.user_filter_group,
            "user_id": self.users.user_id,
            "lower_user_ids": self.users.lower_user_ids,
            "create_only_on_login": self.users.create_only_on_login,
        }

        c = cast(LDAPUserConnectionConfig, {k: v for k, v in r.items() if v is not None})
        return c


def request_ldap_connection(ldap_id: str) -> LDAPConnectionInterface:
    return LDAPConnectionInterface.from_mk_file_format(get_ldap_connections()[ldap_id])


def request_ldap_connections() -> dict[str, LDAPConnectionInterface]:
    return {
        config["id"]: LDAPConnectionInterface.from_mk_file_format(config)
        for config in get_ldap_connections().values()
    }


def update_suffixes(cfg: list[ConfigurableUserConnectionSpec]) -> None:
    LDAPUserConnector.connection_suffixes = {}
    for connection in cfg:
        if connection["type"] == "ldap":
            LDAPUserConnector(connection)


def request_to_delete_ldap_connection(ldap_id: str, pprint_value: bool) -> None:
    config_file = UserConnectionConfigFile()
    all_connections = UserConnectionConfigFile().load_for_modification()
    updated_connections = [c for c in all_connections if c["id"] != ldap_id]
    update_suffixes(updated_connections)
    config_file.save(updated_connections, pprint_value)


def request_to_create_ldap_connection(
    ldap_data: APIConnection, pprint_value: bool
) -> LDAPConnectionInterface:
    connection = LDAPConnectionInterface.from_api_request(ldap_data)
    config_file = UserConnectionConfigFile()
    all_connections = config_file.load_for_modification()
    all_connections.append(connection.to_mk_format())
    update_suffixes(all_connections)
    config_file.save(all_connections, pprint_value)
    return connection


def request_to_edit_ldap_connection(
    ldap_id: str, ldap_data: APIConnection, pprint_value: bool
) -> LDAPConnectionInterface:
    if ldap_data["ldap_connection"]["connection_suffix"]["state"] == "enabled":
        for ldap_connection in [
            cnx for ldapid, cnx in get_ldap_connections().items() if ldapid != ldap_id
        ]:
            if (suffix := ldap_connection.get("suffix")) is not None:
                if suffix == ldap_data["ldap_connection"]["connection_suffix"]["suffix"]:
                    raise MKUserError(
                        None,
                        _("The suffix '%s' is already in use by another LDAP connection.")
                        % ldap_connection["suffix"],
                    )

    config_file = UserConnectionConfigFile()
    all_connections = config_file.load_for_modification()
    connection = LDAPConnectionInterface.from_api_request(ldap_data)
    modified_connections = [c for c in all_connections if c["id"] != ldap_id]
    modified_connections.append(connection.to_mk_format())
    update_suffixes(modified_connections)
    config_file.save(modified_connections, pprint_value)
    return connection
