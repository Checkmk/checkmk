#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast, Literal

from typing_extensions import get_args, TypedDict

from cmk.gui.userdb import (
    ACTIVE_DIR,
    ActivePlugins,
    CUSTOM_USER_ATTRIBUTE,
    DIR_SERVER_389,
    DISABLE_NOTIFICATIONS,
    FORCE_AUTH_USER,
    get_ldap_connections,
    GroupsToSync,
    ICONS_PER_ITEM,
    LDAPConnectionTypedDict,
    NAV_HIDE_ICONS_TITLE,
    OPEN_LDAP,
    SHOW_MODE,
    START_URL,
    TEMP_UNIT,
    UI_SIDEBAR_POSITIONS,
    UI_THEME,
)


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
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> GeneralProperties:
        return cls(
            id=config["id"],
            description=config["description"],
            comment=config["comment"],
            docu_url=config["docu_url"],
            disabled=config["disabled"],
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
    type: Literal["active_directory_manual", "open_ldap", "389_directory_server"]
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
    bind: tuple[str, tuple[Literal["password", "store"], str]] | None = None
    port: int | None = None
    use_ssl: Literal[True] | None = None
    connect_timeout: float | None = None
    version: Literal[2, 3] | None = None
    page_size: int | None = None
    response_timeout: int | None = None
    suffix: str | None = None

    @classmethod
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> ConnectionConfig:
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
    user_filter: str | None = None
    user_filter_group: str | None = None
    user_id: str | None = None
    lower_user_ids: Literal[True] | None = None
    create_only_on_login: Literal[True] | None = None

    @classmethod
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> Users:
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
            "user_id_case": "dont_convert_to_lowercase"
            if self.lower_user_ids is None
            else "convert_to_lowercase",
            "umlauts_in_user_ids": "keep_umlauts"
            if self.user_id_umlauts == "keep"
            else "replace_umlauts",
            "create_users": "on_sync" if self.create_only_on_login is None else "on_login",
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
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> Groups:
        return cls(
            group_dn=config["group_dn"],
            group_scope=config["group_scope"],
            group_filter=config.get("group_filter"),
            group_member=config.get("group_member"),
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


class APIDisableNotifications(TypedDict):
    temporarily_disable_all_notifications: bool
    custom_time_range: APICustomTimeRange | APICheckboxDisabled


class APIGroupsToSync(TypedDict):
    group_cn: str
    attribute_to_set: API_GROUP_ATTRIBUTE_NAME | str
    value: APIDisableNotifications | str


API_GROUP_ATTRIBUTE_NAME = Literal[
    "disable_notifications",
    "mega_menu_icons",
    "navigation_bar_icons",
    "show_mode",
    "ui_sidebar_position",
    "start_url",
    "temperature_unit",
    "ui_theme",
    "visibility_of_hosts_or_services",
]


class APIGroupsToAttributes(APICheckboxEnabled):
    handle_nested: bool
    sync_from_other_connections: list[str]
    groups_to_sync: list[APIGroupsToSync]


class APIGroupsWithConnectionID(TypedDict):
    group_dn: str
    search_in: str


class APIGroupsToRoles(APICheckboxEnabled, total=False):
    admin: list[APIGroupsWithConnectionID]
    agent_registration: list[APIGroupsWithConnectionID]
    guest: list[APIGroupsWithConnectionID]
    user: list[APIGroupsWithConnectionID]


class APISyncPlugins(TypedDict, total=False):
    alias: SYNC_ATTRIBUTE
    authentication_expiration: SYNC_ATTRIBUTE
    disable_notifications: SYNC_ATTRIBUTE
    email_address: SYNC_ATTRIBUTE
    mega_menu_icons: SYNC_ATTRIBUTE
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
) -> list[APIGroupsToSync]:
    api_groups: list[APIGroupsToSync] = []
    value: APIDisableNotifications | str
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
                        "attribute_to_set": "mega_menu_icons",
                        "value": "per_entry" if ii[1] == "entry" else "per_topic",
                    }
                )

            case "nav_hide_icons_title":
                nh = cast(NAV_HIDE_ICONS_TITLE, group["attribute"])
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": "navigation_bar_icons",
                        "value": "do_not_show_title" if nh[1] == "hide" else "show_title",
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
                api_groups.append(
                    {
                        "group_cn": group["cn"],
                        "attribute_to_set": su[0],
                        "value": "default_start_url" if su[1] is None else su[1],
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
                        "value": "show_all" if fa[1] is None else "show_for_user_contacts_only",
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


@dataclass
class SyncPlugins:
    active_plugins: ActivePlugins

    @classmethod
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> SyncPlugins:
        return cls(active_plugins=config["active_plugins"])

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
            "mega_menu_icons": checkbox_state("icons_per_item"),
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
                groups_to_roles[k] = [  # type: ignore[literal-required]
                    {
                        "group_dn": groupdn,
                        "search_in": search_in if search_in is not None else "this_connection",
                    }
                    for groupdn, search_in in v
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
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> Other:
        return cls(cache_livetime=config["cache_livetime"])

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
    def from_mk_file_format(cls, config: LDAPConnectionTypedDict) -> LDAPConnectionInterface:
        return cls(
            general_properties=GeneralProperties.from_mk_file_format(config),
            connection_config=ConnectionConfig.from_mk_file_format(config),
            users=Users.from_mk_file_format(config),
            groups=Groups.from_mk_file_format(config),
            sync_plugins=SyncPlugins.from_mk_file_format(config),
            other=Other.from_mk_file_format(config),
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


def request_ldap_connection(ldap_id: str) -> LDAPConnectionInterface:
    return LDAPConnectionInterface.from_mk_file_format(get_ldap_connections()[ldap_id])


def request_ldap_connections() -> dict[str, LDAPConnectionInterface]:
    return {
        config["id"]: LDAPConnectionInterface.from_mk_file_format(config)
        for config in get_ldap_connections().values()
    }
