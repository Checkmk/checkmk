#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast, Literal, NewType, NotRequired, override, TypedDict

from cmk.ccc import store

from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.type_defs import DisableNotificationsAttribute
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoListConfigFile
from cmk.gui.watolib.utils import multisite_dir

from ._connector import ConnectorType, user_connector_registry, UserConnectionConfig, UserConnector


class HtpasswdUserConnectionConfig(UserConnectionConfig):
    type: Literal["htpasswd"]


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


class LDAPUserConnectionConfig(UserConnectionConfig):
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
    type: Literal["ldap"]


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


class SAMLUserConnectionConfig(UserConnectionConfig, total=True):
    name: str
    description: str
    comment: str
    docu_url: str
    idp_metadata: tuple[str, str] | tuple[str, tuple[str, str, bytes]]
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
    type: Literal["saml2"]
    version: Literal["1.0.0"]
    owned_by_site: str
    customer: NotRequired[str]


ConfigurableUserConnectionSpec = LDAPUserConnectionConfig | SAMLUserConnectionConfig


@request_memoize(maxsize=None)
def get_connection(connection_id: str | None) -> UserConnector | None:
    """Returns the connection object of the requested connection id

    This function maintains a cache that for a single connection_id only one object per request is
    created."""
    connections_with_id = [c for cid, c in _all_connections() if cid == connection_id]
    return connections_with_id[0] if connections_with_id else None


def active_connections_by_type(connection_type: str) -> list[dict[str, Any]]:
    return [c for c in connections_by_type(connection_type) if not c["disabled"]]


def connections_by_type(connection_type: str) -> list[dict[str, Any]]:
    return [c for c in _get_connection_configs() if c["type"] == connection_type]


def clear_user_connection_cache() -> None:
    get_connection.cache_clear()  # type: ignore[attr-defined]


def active_connections() -> list[tuple[str, UserConnector]]:
    enabled_configs = [cfg for cfg in _get_connection_configs() if not cfg["disabled"]]  #
    return [
        (connection_id, connection)  #
        for connection_id, connection in _get_connections_for(enabled_configs)
        if connection.is_enabled()
    ]


def connection_choices() -> list[tuple[str, str]]:
    return sorted(
        [
            (connection_id, f"{connection_id} ({connection.type()})")
            for connection_id, connection in _all_connections()
            if connection.type() == ConnectorType.LDAP
        ],
        key=lambda id_and_description: id_and_description[1],
    )


def _all_connections() -> list[tuple[str, UserConnector]]:
    return _get_connections_for(_get_connection_configs())


def _get_connections_for(configs: list[dict[str, Any]]) -> list[tuple[str, UserConnector]]:
    return [(cfg["id"], user_connector_registry[cfg["type"]](cfg)) for cfg in configs]


def _get_connection_configs() -> list[dict[str, Any]]:
    return builtin_connections + active_config.user_connections


_HTPASSWD_CONNECTION = HtpasswdUserConnectionConfig(
    {
        "type": "htpasswd",
        "id": "htpasswd",
        "disabled": False,
    }
)
# The htpasswd connector is enabled by default and always executed first.
# NOTE: This list may be appended to in edition specific registration functions.
builtin_connections: list[UserConnectionConfig] = [_HTPASSWD_CONNECTION]


def get_ldap_connections() -> dict[str, LDAPUserConnectionConfig]:
    ldap_connections = cast(
        dict[str, LDAPUserConnectionConfig],
        {c["id"]: c for c in active_config.user_connections if c["type"] == "ldap"},
    )
    return ldap_connections


def get_active_ldap_connections() -> dict[str, LDAPUserConnectionConfig]:
    return {
        ldap_id: ldap_connection
        for ldap_id, ldap_connection in get_ldap_connections().items()
        if not ldap_connection["disabled"]
    }


def get_saml_connections() -> dict[str, SAMLUserConnectionConfig]:
    saml_connections = cast(
        dict[str, SAMLUserConnectionConfig],
        {c["id"]: c for c in active_config.user_connections if c["type"] == "saml2"},
    )
    return saml_connections


def get_active_saml_connections() -> dict[str, SAMLUserConnectionConfig]:
    return {
        saml_id: saml_connection
        for saml_id, saml_connection in get_saml_connections().items()
        if not saml_connection["disabled"]
    }


def locked_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific locked attributes"""
    return _get_attributes(connection_id, lambda c: c.locked_attributes())


def multisite_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific multisite attributes"""
    return _get_attributes(connection_id, lambda c: c.multisite_attributes())


def non_contact_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific non contact attributes"""
    return _get_attributes(connection_id, lambda c: c.non_contact_attributes())


def _get_attributes(
    connection_id: str | None, selector: Callable[[UserConnector], Sequence[str]]
) -> Sequence[str]:
    connection = get_connection(connection_id)
    return selector(connection) if connection else []


UserConnections = list[ConfigurableUserConnectionSpec] | Sequence[ConfigurableUserConnectionSpec]


def load_connection_config(lock: bool = False) -> UserConnections:
    if lock:
        return UserConnectionConfigFile().load_for_modification()
    return UserConnectionConfigFile().load_for_reading()


def save_connection_config(connections: list[ConfigurableUserConnectionSpec]) -> None:
    """Save the connections for the Setup

    Note:
        This function should only be used in the Setup context, when configuring
        the connections. During UI rendering, `active_config.user_connections` must
        be used.
    """
    UserConnectionConfigFile().save(connections, pprint_value=active_config.wato_pprint_config)


def save_snapshot_user_connection_config(
    connections: list[Mapping[str, Any]],
    snapshot_work_dir: str,
) -> None:
    save_dir = Path(snapshot_work_dir, "etc/check_mk/multisite.d/wato")
    save_dir.mkdir(mode=0o770, parents=True, exist_ok=True)
    store.save_to_mk_file(
        save_dir / "user_connections.mk", key="user_connections", value=connections
    )

    for connector_class in user_connector_registry.values():
        connector_class.config_changed()

    clear_user_connection_cache()


class UserConnectionConfigFile(WatoListConfigFile[ConfigurableUserConnectionSpec]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=multisite_dir() / "user_connections.mk",
            config_variable="user_connections",
            spec_class=ConfigurableUserConnectionSpec,
        )

    @override
    def save(self, cfg: list[ConfigurableUserConnectionSpec], pprint_value: bool) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            self._config_file_path,
            key=self._config_variable,
            value=cfg,
            pprint_value=pprint_value,
        )

        for connector_class in user_connector_registry.values():
            connector_class.config_changed()

        clear_user_connection_cache()


def register_config_file(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(UserConnectionConfigFile())
