#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Literal, NewType, NotRequired, TypedDict

from cmk.gui.type_defs import DisableNotificationsAttribute


class HtpasswdUserConnectionConfig(TypedDict):
    type: Literal["htpasswd"]
    id: str
    disabled: bool


class OAuth2UserConnectionConfig(TypedDict):
    type: Literal["oauth2"]
    id: str
    disabled: bool


class Fixed(TypedDict):
    server: str
    failover_servers: NotRequired[list[str]]


class Discover(TypedDict):
    domain: str


class LDAPConnectionConfigFixed(TypedDict):
    connect_to: tuple[Literal["fixed_list"], Fixed]


class LDAPConnectionConfigDiscover(TypedDict):
    connect_to: tuple[Literal["discover"], Discover]


class SyncAttribute(TypedDict, total=True):
    attr: NotRequired[str]


class GroupsToContactGroups(TypedDict, total=True):
    nested: NotRequired[Literal[True]]
    other_connections: NotRequired[list[str]]


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


class GroupsToSync(TypedDict):
    cn: str
    attribute: ATTRIBUTE


class GroupsToAttributes(TypedDict, total=True):
    nested: NotRequired[Literal[True]]
    other_connections: NotRequired[list[str]]
    groups: list[GroupsToSync]


RoleSpec = tuple[str, str | None]


class GroupsToRoles(TypedDict, total=False):
    nested: NotRequired[Literal[True]]
    admin: NotRequired[list[RoleSpec]]
    agent_registration: NotRequired[list[RoleSpec]]
    guest: NotRequired[list[RoleSpec]]
    user: NotRequired[list[RoleSpec]]
    no_permissions: NotRequired[list[RoleSpec]]


class ActivePlugins(TypedDict, total=True):
    alias: NotRequired[SyncAttribute]
    auth_expire: NotRequired[SyncAttribute]
    groups_to_roles: NotRequired[GroupsToRoles]
    groups_to_contactgroups: NotRequired[GroupsToContactGroups]
    groups_to_attributes: NotRequired[GroupsToAttributes]
    disable_notifications: NotRequired[SyncAttribute]
    email: NotRequired[SyncAttribute]
    icons_per_item: NotRequired[SyncAttribute]
    nav_hide_icons_title: NotRequired[SyncAttribute]
    pager: NotRequired[SyncAttribute]
    show_mode: NotRequired[SyncAttribute]
    ui_sidebar_position: NotRequired[SyncAttribute]
    start_url: NotRequired[SyncAttribute]
    temperature_unit: NotRequired[SyncAttribute]
    ui_theme: NotRequired[SyncAttribute]
    force_authuser: NotRequired[SyncAttribute]


DIR_SERVER_389 = tuple[Literal["389directoryserver"], LDAPConnectionConfigFixed]
OPEN_LDAP = tuple[Literal["openldap"], LDAPConnectionConfigFixed]
ACTIVE_DIR = tuple[Literal["ad"], LDAPConnectionConfigFixed | LDAPConnectionConfigDiscover]


class LDAPUserConnectionConfig(TypedDict):
    type: Literal["ldap"]
    id: str
    disabled: bool
    description: str
    comment: str
    docu_url: str
    directory_type: DIR_SERVER_389 | OPEN_LDAP | ACTIVE_DIR
    bind: NotRequired[tuple[str, tuple[Literal["password", "store"], str]]]
    port: NotRequired[int]
    use_ssl: NotRequired[Literal[True]]
    connect_timeout: NotRequired[float]
    version: NotRequired[Literal[2, 3]]
    page_size: NotRequired[int]
    response_timeout: NotRequired[int]
    suffix: NotRequired[str]
    user_dn: str
    user_scope: Literal["sub", "base", "one"]
    user_id_umlauts: Literal["keep", "replace"]
    user_filter: NotRequired[str]
    user_filter_group: NotRequired[str]
    user_id: NotRequired[str]
    lower_user_ids: NotRequired[Literal[True]]
    create_only_on_login: NotRequired[Literal[True]]
    group_dn: str
    group_scope: Literal["sub", "base", "one"]
    group_filter: NotRequired[str]
    group_member: NotRequired[str]
    active_plugins: ActivePlugins
    cache_livetime: int
    customer: NotRequired[str | None]


# these need to be written to a .mk file, so a more complex type like Path will lead to problems
PrivateKeyPath = NewType("PrivateKeyPath", str)
PublicKeyPath = NewType("PublicKeyPath", str)


class ContactGroupMapping(TypedDict):
    attribute_match_value: str
    contact_group_ids: Sequence[str]


# TODO: This type is horrible, one can't even dispatch to the right alternative at runtime without
#  looking at the *values*. This must be done differently, so dispatching can be done on the *types*
ContactGroupMappingSpec = (
    str | tuple[str, dict[str, str]] | tuple[str, dict[str, str | Sequence[ContactGroupMapping]]]
)
SerializedCertificateSpec = (
    Literal["builtin"] | tuple[Literal["custom"], tuple[PrivateKeyPath, PublicKeyPath]]
)
ROLE_MAPPING = Literal[False] | tuple[Literal[True], tuple[str, Mapping[str, Sequence[str]]]]


class SAMLRequestedAuthnContext(TypedDict):
    comparison: Literal["exact", "minimum", "maximum", "better"]
    authn_context_class_ref: Sequence[str]


SAML_IDP_METADATA = (
    tuple[Literal["url"], str]
    | tuple[Literal["text"], str]
    | tuple[Literal["file"], tuple[str, str, bytes]]
)


class SAMLUserConnectionConfig(TypedDict, total=True):
    type: Literal["saml2"]
    id: str
    disabled: bool
    name: str
    description: str
    comment: str
    docu_url: str
    idp_metadata: SAML_IDP_METADATA
    checkmk_entity_id: str
    checkmk_metadata_endpoint: str
    checkmk_assertion_consumer_service_endpoint: str
    checkmk_server_url: str
    connection_timeout: tuple[int, int]  # connection timeout, read timeout
    signature_certificate: SerializedCertificateSpec
    encryption_certificate: NotRequired[SerializedCertificateSpec]
    requested_authn_context: NotRequired[SAMLRequestedAuthnContext]
    user_id_attribute_name: str
    user_alias_attribute_name: str
    email_attribute_name: str
    contactgroups_mapping: ContactGroupMappingSpec
    role_membership_mapping: ROLE_MAPPING
    version: Literal["1.0.0"]
    owned_by_site: str
    customer: NotRequired[str]


ConfigurableUserConnectionSpec = LDAPUserConnectionConfig | SAMLUserConnectionConfig
UserConnectionConfig = (
    HtpasswdUserConnectionConfig | OAuth2UserConnectionConfig | ConfigurableUserConnectionSpec
)
