#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NewType, TypedDict

from pydantic import BaseModel, Field

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD

# these need to be written to a .mk file, so a more complex type like Path will lead to problems
PrivateKeyPath = NewType("PrivateKeyPath", str)
PublicKeyPath = NewType("PublicKeyPath", str)


class Discover(BaseModel):
    domain: str


class LDAPConnectionConfigDiscover(BaseModel):
    connect_to: tuple[Literal["discover"], Discover]


class Fixed(BaseModel):
    server: str
    failover_servers: list[str] | Omitted = OMITTED_FIELD


class LDAPConnectionConfigFixed(BaseModel):
    connect_to: tuple[Literal["fixed_list"], Fixed]


DIR_SERVER_389 = tuple[Literal["389directoryserver"], LDAPConnectionConfigFixed]
OPEN_LDAP = tuple[Literal["openldap"], LDAPConnectionConfigFixed]
ACTIVE_DIR = tuple[Literal["ad"], LDAPConnectionConfigFixed | LDAPConnectionConfigDiscover]


class DisableNotificationsAttribute(BaseModel):
    disable: Literal[True] | Omitted = OMITTED_FIELD
    timerange: tuple[float, float] | Omitted = OMITTED_FIELD


DISABLE_NOTIFICATIONS = tuple[Literal["disable_notifications"], DisableNotificationsAttribute]
ICONS_PER_ITEM = tuple[Literal["icons_per_item"], None | Literal["entry"]]
NAV_HIDE_ICONS_TITLE = tuple[Literal["nav_hide_icons_title"], None | Literal["hide"]]
SHOW_MODE = tuple[
    Literal["show_mode"],
    None | Literal["default_show_less", "default_show_more", "enforce_show_more"],
]
UI_SIDEBAR_POSITIONS = tuple[Literal["ui_sidebar_position"], None | Literal["left"]]
START_URL = tuple[Literal["start_url"], None | str]
TEMP_UNIT = tuple[Literal["temperature_unit"], None | Literal["celsius", "fahrenheit"]]
UI_THEME = tuple[Literal["ui_theme"], None | Literal["facelift", "modern-dark"]]
FORCE_AUTH_USER = tuple[Literal["force_authuser"], bool]
CUSTOM_USER_ATTRIBUTE = tuple[str, str]


ATTRIBUTE = (
    DISABLE_NOTIFICATIONS
    | ICONS_PER_ITEM
    | NAV_HIDE_ICONS_TITLE
    | SHOW_MODE
    | UI_SIDEBAR_POSITIONS
    | START_URL
    | TEMP_UNIT
    | UI_THEME
    | FORCE_AUTH_USER
    | CUSTOM_USER_ATTRIBUTE
)


class GroupsToSync(BaseModel):
    cn: str
    attribute: ATTRIBUTE


class GroupsToAttributes(BaseModel):
    nested: Literal[True] | Omitted = OMITTED_FIELD
    other_connections: list[str] | Omitted = OMITTED_FIELD
    groups: list[GroupsToSync] = Field(min_length=1)


class GroupsToContactGroups(BaseModel):
    nested: Literal[True] | Omitted = OMITTED_FIELD
    other_connections: list[str] | Omitted = OMITTED_FIELD


class SyncAttribute(BaseModel):
    attr: str | Omitted = OMITTED_FIELD


class ActivePlugins(BaseModel):
    alias: SyncAttribute | Omitted = OMITTED_FIELD
    auth_expire: SyncAttribute | Omitted = OMITTED_FIELD
    groups_to_roles: dict[str, list[tuple[str, str | None]]] | Omitted = OMITTED_FIELD
    groups_to_contactgroups: GroupsToContactGroups | Omitted = OMITTED_FIELD
    groups_to_attributes: GroupsToAttributes | Omitted = OMITTED_FIELD
    disable_notifications: SyncAttribute | Omitted = OMITTED_FIELD
    email: SyncAttribute | Omitted = OMITTED_FIELD
    icons_per_item: SyncAttribute | Omitted = OMITTED_FIELD
    nav_hide_icons_title: SyncAttribute | Omitted = OMITTED_FIELD
    pager: SyncAttribute | Omitted = OMITTED_FIELD
    show_mode: SyncAttribute | Omitted = OMITTED_FIELD
    ui_sidebar_position: SyncAttribute | Omitted = OMITTED_FIELD
    start_url: SyncAttribute | Omitted = OMITTED_FIELD
    temperature_unit: SyncAttribute | Omitted = OMITTED_FIELD
    ui_theme: SyncAttribute | Omitted = OMITTED_FIELD
    force_authuser: SyncAttribute | Omitted = OMITTED_FIELD


class LDAPConnectionModel(BaseModel):
    id: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    directory_type: DIR_SERVER_389 | OPEN_LDAP | ACTIVE_DIR
    bind: tuple[str, tuple[Literal["password", "store"], str]] | Omitted = OMITTED_FIELD
    port: int | Omitted = OMITTED_FIELD
    use_ssl: Literal[True] | Omitted = OMITTED_FIELD
    connect_timeout: float | Omitted = OMITTED_FIELD
    version: Literal[2, 3] | Omitted = OMITTED_FIELD
    page_size: int | Omitted = OMITTED_FIELD
    response_timeout: int | Omitted = OMITTED_FIELD
    suffix: str | Omitted = OMITTED_FIELD
    user_dn: str
    user_scope: Literal["sub", "base", "one"]
    user_id_umlauts: Literal["keep", "replace"]
    user_filter: str | Omitted = OMITTED_FIELD
    user_filter_group: str | Omitted = OMITTED_FIELD
    user_id: str | Omitted = OMITTED_FIELD
    lower_user_ids: Literal[True] | Omitted = OMITTED_FIELD
    create_only_on_login: Literal[True] | Omitted = OMITTED_FIELD
    group_dn: str
    group_scope: Literal["sub", "base", "one"]
    group_filter: str | Omitted = OMITTED_FIELD
    group_member: str | Omitted = OMITTED_FIELD
    active_plugins: ActivePlugins
    cache_livetime: int
    customer: str | None | Omitted = OMITTED_FIELD
    type: Literal["ldap"]


class ContactGroupMapping(TypedDict):
    attribute_match_value: str
    contact_group_ids: Sequence[str]


# TODO: This type is horrible, one can't even dispatch to the right alternative at runtime without
# looking at the *values*. This must be done differently, so dispatching can be done on the *types*
ContactGroupMappingSpec = (
    str | tuple[str, dict[str, str]] | tuple[str, dict[str, str | Sequence[ContactGroupMapping]]]
)
SerializedCertificateSpec = (
    Literal["builtin"] | tuple[Literal["custom"], tuple[PrivateKeyPath, PublicKeyPath]]
)
IDP_METADATA = tuple[Literal["url"], str] | tuple[Literal["xml"], str]
ROLE_MAPPING = Literal[False] | tuple[Literal[True], tuple[str, dict[str, list[str]]]]


class SAMLConnectionModel(BaseModel):
    type: Literal["saml2"]
    version: Literal["1.0.0"]
    owned_by_site: str
    customer: str | Omitted = OMITTED_FIELD
    id: str
    name: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    idp_metadata: IDP_METADATA
    checkmk_entity_id: str
    checkmk_metadata_endpoint: str
    checkmk_assertion_consumer_service_endpoint: str
    checkmk_server_url: str
    connection_timeout: tuple[int, int]  # connection timeout, read timeout
    signature_certificate: SerializedCertificateSpec
    encryption_certificate: SerializedCertificateSpec | Omitted = OMITTED_FIELD
    user_id_attribute_name: str
    user_alias_attribute_name: str
    email_attribute_name: str
    contactgroups_mapping: ContactGroupMappingSpec
    role_membership_mapping: ROLE_MAPPING
