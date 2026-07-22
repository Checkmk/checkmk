#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import assert_never, Literal, overload, override, TypeGuard

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.site import omd_site, SiteId
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.site_config import is_distributed_setup_remote_site, site_is_local
from cmk.gui.user_connection_config_types import (
    ConfigurableUserConnectionSpec,
    HtpasswdUserConnectionConfig,
    LDAPUserConnectionConfig,
    SAMLUserConnectionConfig,
    UserConnectionConfig,
)
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.pending_changes import Change, ChangeScope, PendingChanges
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoListConfigFile
from cmk.gui.watolib.utils import multisite_dir
from cmk.livestatus_client import (
    AuthenticationConnectionEntry,
    AuthenticationConnectionsValue,
    SAMLAuthenticationEntry,
    SiteConfiguration,
    SiteConfigurations,
)
from cmk.utils import paths

from ._connector import ConnectorType, user_connector_registry, UserConnector


@request_memoize(maxsize=None)
def get_connection(connection_id: str | None) -> UserConnector | None:
    """Returns the connection object of the requested connection id

    This function maintains a cache that for a single connection_id only one object per request is
    created."""
    connections_with_id = [
        c for cid, c in _all_connections(active_config.user_connections) if cid == connection_id
    ]
    return connections_with_id[0] if connections_with_id else None


def get_connection_uncached(
    connection_id: str, user_connections: Sequence[UserConnectionConfig]
) -> UserConnector | None:
    for connection_config in _get_connection_configs(user_connections):
        if connection_config["id"] == connection_id:
            return user_connector_registry[connection_config["type"]](connection_config)
    return None


@overload
def connections_by_type(connection_type: Literal["ldap"]) -> list[LDAPUserConnectionConfig]: ...
@overload
def connections_by_type(connection_type: Literal["saml2"]) -> list[SAMLUserConnectionConfig]: ...


def connections_by_type(
    connection_type: Literal["saml2", "ldap"],
) -> list[LDAPUserConnectionConfig] | list[SAMLUserConnectionConfig]:
    match connection_type:
        case "ldap":
            return [c for c in active_config.user_connections if is_ldap(c)]
        case "saml2":
            return [c for c in active_config.user_connections if is_saml(c)]
        case _:
            assert_never(connection_type)


def is_ldap(c: ConfigurableUserConnectionSpec) -> TypeGuard[LDAPUserConnectionConfig]:
    return c["type"] == "ldap"


def is_saml(c: ConfigurableUserConnectionSpec) -> TypeGuard[SAMLUserConnectionConfig]:
    return c["type"] == "saml2"


def clear_user_connection_cache() -> None:
    get_connection.cache_clear()  # type: ignore[attr-defined]


def active_connections(
    user_connections: Sequence[UserConnectionConfig],
) -> list[tuple[str, UserConnector]]:
    enabled_configs = [
        cfg for cfg in _get_connection_configs(user_connections) if not cfg["disabled"]
    ]
    return [
        (connection_id, connection)
        for connection_id, connection in _get_connections_for(enabled_configs)
        if connection.is_enabled()
    ]


def connection_choices() -> list[tuple[str, str]]:
    return sorted(
        [
            (connection_id, f"{connection_id} ({connection.type()})")
            for connection_id, connection in _all_connections(active_config.user_connections)
            if connection.type() == ConnectorType.LDAP
        ],
        key=lambda id_and_description: id_and_description[1],
    )


def saml_connection_choices() -> list[tuple[str, str]]:
    """SAML connections that can be picked for site-level authentication."""
    return sorted(
        [
            (connection_id, f"{connection_id} ({ConnectorType.SAML2})")
            for connection_id in get_saml_connections()
        ],
        key=lambda id_and_description: id_and_description[1],
    )


def _all_connections(
    user_connections: Sequence[UserConnectionConfig],
) -> list[tuple[str, UserConnector]]:
    return _get_connections_for(_get_connection_configs(user_connections))


def _get_connections_for(
    configs: Sequence[UserConnectionConfig],
) -> list[tuple[str, UserConnector]]:
    return [(cfg["id"], user_connector_registry[cfg["type"]](cfg)) for cfg in configs]


def _get_connection_configs(
    user_connections: Sequence[UserConnectionConfig],
) -> list[UserConnectionConfig]:
    return [*builtin_connections, *user_connections]


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
    return {c["id"]: c for c in active_config.user_connections if is_ldap(c)}


def get_active_ldap_connections() -> dict[str, LDAPUserConnectionConfig]:
    return {
        ldap_id: ldap_connection
        for ldap_id, ldap_connection in get_ldap_connections().items()
        if not ldap_connection["disabled"]
    }


def get_saml_connections() -> dict[str, SAMLUserConnectionConfig]:
    return {c["id"]: c for c in active_config.user_connections if is_saml(c)}


def get_active_saml_connections() -> dict[str, SAMLUserConnectionConfig]:
    return {
        saml_id: saml_connection
        for saml_id, saml_connection in get_saml_connections().items()
        if not saml_connection["disabled"]
    }


def distributed_saml_supported() -> bool:
    return cmk_version.edition(paths.omd_root) not in (
        cmk_version.Edition.COMMUNITY,
        cmk_version.Edition.CLOUD,
    )


def _connection_available_on_site(
    connection_config: Mapping[str, object], site_config: SiteConfiguration
) -> bool:
    if site_is_local(site_config):
        return True
    _customer_api = customer_api()
    customer = _customer_api.get_customer_id(connection_config)
    if _customer_api.is_global(customer):
        return True
    assert customer is not None
    return site_config["id"] in _customer_api.get_sites_of_customer(customer)


def ldap_authentication_entries_for_site(
    ldap_connections: Mapping[str, LDAPUserConnectionConfig],
    site_config: SiteConfiguration,
) -> list[AuthenticationConnectionEntry]:
    return [
        ("ldap", connection_id)
        for connection_id, ldap_connection in sorted(ldap_connections.items())
        if _connection_available_on_site(ldap_connection, site_config)
    ]


# `authentication_connections` is always written by the site editor and by
# cmk-update-config, but specs constructed in code may omit it. Missing means
# the legacy behavior: every configured connection may authenticate users.
_DEFAULT_AUTHENTICATION_CONNECTIONS: AuthenticationConnectionsValue = ("all", ["ldap", "saml"])


def _expand_to_available_connections(
    value: AuthenticationConnectionsValue,
    site_config: SiteConfiguration,
) -> list[AuthenticationConnectionEntry]:
    """Resolve an on-disk `authentication_connections` value into a concrete list."""
    if value == "disabled":
        return []
    if isinstance(value, list):
        return value
    _all, connection_types = value
    expanded: list[AuthenticationConnectionEntry] = []
    if "ldap" in connection_types:
        expanded += ldap_authentication_entries_for_site(get_active_ldap_connections(), site_config)
    if "saml" in connection_types and distributed_saml_supported():
        expanded += [
            ("saml", SAMLAuthenticationEntry(connection_id=connection_id))
            for connection_id, saml_connection in sorted(get_active_saml_connections().items())
            if _connection_available_on_site(saml_connection, site_config)
        ]
    return expanded


def resolved_authentication_connections(
    site_config: SiteConfiguration,
) -> list[AuthenticationConnectionEntry]:
    """The connections a site ends up with, determined on the central site to propagate them."""
    return _expand_to_available_connections(
        site_config.get("authentication_connections", _DEFAULT_AUTHENTICATION_CONNECTIONS),
        site_config,
    )


def effective_authentication_connections(
    site_config: SiteConfiguration,
) -> list[AuthenticationConnectionEntry]:
    """The connections a site actually authenticates users against at runtime."""
    if is_distributed_setup_remote_site(active_config.sites):
        # sites.mk is not synchronized to remotes, so `site_config` is only the seeded
        # local self-default. The connections propagated by get_site_globals(), carrying
        # per-site ACS URLs and restrictions, are the source of truth here.
        return active_config.authentication_connections or []
    return resolved_authentication_connections(site_config)


def _referenced_connection_id(entry: AuthenticationConnectionEntry) -> str:
    if entry[0] == "ldap":
        return entry[1]
    return entry[1]["connection_id"]


def _references_connection(entry: AuthenticationConnectionEntry, connection_id: str) -> bool:
    return _referenced_connection_id(entry) == connection_id


def _explicitly_references_connection(site_config: SiteConfiguration, connection_id: str) -> bool:
    value = site_config.get("authentication_connections", _DEFAULT_AUTHENTICATION_CONNECTIONS)
    if not isinstance(value, list):
        # "disabled" references nothing; the ("all", [types]) form is
        # resolved dynamically and simply skips connections that are not
        # available on the site — no dead reference can remain.
        return False
    return any(_references_connection(entry, connection_id) for entry in value)


def sites_with_dangling_login_reference(
    site_configs: SiteConfigurations,
    connection_id: str,
    customer: str | None,
) -> list[SiteId]:
    """Sites that reference the connection for login but would no longer receive it.

    In the ultimatemt edition a connection is only synchronized to the sites of its
    customer (or to all sites if it is scoped globally). A remote site that explicitly
    lists the connection in its ``authentication_connections`` but belongs to a
    different customer would be left with a dead login reference. The central site is
    exempt: as the configuration master it always has every connection.

    Sites using the ``("all", [types])`` shorthand (or lacking the key, which defaults
    to it) resolve their connections dynamically and simply skip connections that are
    not available on the site — those are not reported here. ``"disabled"`` references
    nothing.

    Outside the ultimatemt edition the customer API stub treats every scope as global,
    so this always returns an empty list.
    """
    _customer_api = customer_api()
    if _customer_api.is_global(customer):
        return []
    assert customer is not None
    receiving_sites = set(_customer_api.get_sites_of_customer(customer))
    return [
        site_id
        for site_id, site_config in site_configs.items()
        if site_id not in receiving_sites
        and not site_is_local(site_config)
        and _explicitly_references_connection(site_config, connection_id)
    ]


def login_connections_of_other_customer(
    site_config: SiteConfiguration,
    all_connections: Iterable[ConfigurableUserConnectionSpec],
) -> list[str]:
    """Login connections the site references but that belong to a different customer.

    The mirror image of :func:`sites_with_dangling_login_reference`: here a site's
    customer is changing, and every connection it lists in its
    ``authentication_connections`` must be scoped either globally or to the site's (new)
    customer. A connection scoped to a different customer is not synchronized to the
    site, so the login reference would be dead after the change. The IDs of such
    connections are returned (deduplicated, in reference order).

    The central site is exempt: as the configuration master it always has every
    connection. Connections the site references but that no longer exist are ignored;
    they are dangling for an unrelated reason and not this check's concern.

    Outside the ultimatemt edition the customer API stub treats every scope as global,
    so this always returns an empty list.
    """
    if site_is_local(site_config):
        return []
    auth_connections = site_config["authentication_connections"]
    if not isinstance(auth_connections, list):
        # "disabled" references nothing; the ("all", [types]) form is
        # resolved dynamically and simply skips connections that are not
        # available on the site, no dead reference can arise.
        return []
    _customer_api = customer_api()
    site_customer = _customer_api.get_customer_id(site_config)
    connections_by_id = {connection["id"]: connection for connection in all_connections}
    conflicting: list[str] = []
    for entry in auth_connections:
        connection_id = _referenced_connection_id(entry)
        if connection_id in conflicting:
            continue
        if (connection := connections_by_id.get(connection_id)) is None:
            continue
        connection_customer = _customer_api.get_customer_id(connection)
        if _customer_api.is_global(connection_customer):
            continue
        if connection_customer != site_customer:
            conflicting.append(connection_id)
    return conflicting


def _resolve_authentication_connections(
    auth_connections: list[AuthenticationConnectionEntry],
    available: dict[str, SAMLUserConnectionConfig],
) -> dict[str, SAMLUserConnectionConfig]:
    """Resolve the SAML connections available on the current site.

    Only ``("saml", {connection_id})`` entries contribute SAML connections.
    """
    resolved: dict[str, SAMLUserConnectionConfig] = {}
    for entry in auth_connections:
        if entry[0] != "saml":
            continue
        connection_id = entry[1]["connection_id"]
        if (cfg := available.get(connection_id)) is None:
            continue
        resolved[connection_id] = cfg
    return resolved


def get_saml_connections_for_current_site() -> dict[str, SAMLUserConnectionConfig]:
    """SAML connections available for login authentication on the current site.

    Returns the connections explicitly listed in the site's
    `authentication_connections`. On the central site the data lives in
    `sites.mk`; on a remote site it arrives via the global
    `authentication_connections` populated by `get_site_globals()`.
    """
    return _resolve_authentication_connections(
        effective_authentication_connections(active_config.sites[omd_site()]),
        get_active_saml_connections(),
    )


UserConnections = list[ConfigurableUserConnectionSpec] | Sequence[ConfigurableUserConnectionSpec]


def load_connection_config(lock: bool = False) -> UserConnections:
    if lock:
        return UserConnectionConfigFile().load_for_modification()
    return UserConnectionConfigFile().load_for_reading()


def save_snapshot_user_connection_config(
    connections: Sequence[ConfigurableUserConnectionSpec],
    snapshot_work_dir: str,
) -> None:
    save_dir = Path(snapshot_work_dir, "etc/check_mk/multisite.d/wato")
    save_dir.mkdir(mode=0o770, parents=True, exist_ok=True)
    store.save_to_mk_file(
        save_dir / "user_connections.mk", key="user_connections", value=list(connections)
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

    def update(
        self,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_id: str,
        connection_type: Literal["ldap", "saml2"],
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain],
        pprint_value: bool,
        pending_changes: PendingChanges,
    ) -> None:
        pending_changes.add(
            Change(
                action_name=f"edit-{connection_type}-connection",
                text=_("Changed %(connection_type)s connection %(connection_id)s")
                % {"connection_type": connection_type.upper(), "connection_id": connection_id},
                domains=[d.ident() for d in domains],
            ),
            ChangeScope.sites(sites),
        )
        self.save(cfg, pprint_value=pprint_value)

    def create(
        self,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_type: Literal["ldap", "saml2"],
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain],
        pprint_value: bool,
        pending_changes: PendingChanges,
    ) -> None:
        pending_changes.add(
            Change(
                action_name=f"new-{connection_type}-connection",
                text=_("Created new %(connection_type)s connection")
                % {"connection_type": connection_type.upper()},
                domains=[d.ident() for d in domains],
            ),
            ChangeScope.sites(sites),
        )
        self.save(cfg, pprint_value=pprint_value)

    def delete(
        self,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_id: str,
        connection_type: Literal["ldap", "saml2"],
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain],
        pprint_value: bool,
        pending_changes: PendingChanges,
    ) -> None:
        pending_changes.add(
            Change(
                action_name=f"delete-{connection_type}-connection",
                text=_("Deleted %(connection_type)s connection %(connection_id)s")
                % {"connection_type": connection_type.upper(), "connection_id": connection_id},
                domains=[d.ident() for d in domains],
            ),
            ChangeScope.sites(sites),
        )
        self.save(cfg, pprint_value=pprint_value)

    def move(
        self,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_id: str,
        connection_type: Literal["ldap", "saml2"],
        to_index: int,
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain],
        pprint_value: bool,
        pending_changes: PendingChanges,
    ) -> None:
        pending_changes.add(
            Change(
                action_name=f"move-{connection_type}-connection",
                text=_("Changed position of connection %(connection_id)s to %(to_index)d")
                % {"connection_id": connection_id, "to_index": to_index},
                domains=[d.ident() for d in domains],
            ),
            ChangeScope.sites(sites),
        )
        self.save(cfg, pprint_value=pprint_value)


def register_config_file(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(UserConnectionConfigFile())
