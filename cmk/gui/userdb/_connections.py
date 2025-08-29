#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, assert_never, Literal, overload, override, TypeGuard

from cmk.ccc import store
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.user_connection_config_types import (
    ConfigurableUserConnectionSpec,
    HtpasswdUserConnectionConfig,
    LDAPUserConnectionConfig,
    SAMLUserConnectionConfig,
    UserConnectionConfig,
)
from cmk.gui.watolib import changes as _changes
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoListConfigFile
from cmk.gui.watolib.utils import multisite_dir

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


UserConnections = list[ConfigurableUserConnectionSpec] | Sequence[ConfigurableUserConnectionSpec]


def load_connection_config(lock: bool = False) -> UserConnections:
    if lock:
        return UserConnectionConfigFile().load_for_modification()
    return UserConnectionConfigFile().load_for_reading()


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

    def update(
        self,
        user_id: UserId | None,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_id: str,
        connection_type: Literal["ldap", "saml2"],
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain] | None,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        _changes.add_change(
            action_name=f"edit-{connection_type}-connection",
            text=_("Changed %s connection %s") % (connection_type.upper(), connection_id),
            user_id=user_id,
            domains=domains,
            sites=sites,
            use_git=use_git,
        )
        self.save(cfg, pprint_value=pprint_value)

    def create(
        self,
        user_id: UserId | None,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_type: Literal["ldap", "saml2"],
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain] | None,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        _changes.add_change(
            action_name=f"new-{connection_type}-connection",
            text=_("Created new %s connection") % connection_type.upper(),
            user_id=user_id,
            domains=domains,
            sites=sites,
            use_git=use_git,
        )
        self.save(cfg, pprint_value=pprint_value)

    def delete(
        self,
        user_id: UserId | None,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_id: str,
        connection_type: Literal["ldap", "saml2"],
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain] | None,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        _changes.add_change(
            action_name=f"delete-{connection_type}-connection",
            text=_("Deleted %s connection %s") % (connection_type.upper(), connection_id),
            user_id=user_id,
            domains=domains,
            sites=sites,
            use_git=use_git,
        )
        self.save(cfg, pprint_value=pprint_value)

    def move(
        self,
        user_id: UserId | None,
        cfg: list[ConfigurableUserConnectionSpec],
        connection_id: str,
        connection_type: Literal["ldap", "saml2"],
        to_index: int,
        sites: list[SiteId],
        domains: Sequence[ABCConfigDomain] | None,
        pprint_value: bool,
        use_git: bool,
    ) -> None:
        _changes.add_change(
            action_name=f"move-{connection_type}-connection",
            text=_("Changed position of connection %s to %d") % (connection_id, to_index),
            user_id=user_id,
            domains=domains,
            sites=sites,
            use_git=use_git,
        )
        self.save(cfg, pprint_value=pprint_value)


def register_config_file(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(UserConnectionConfigFile())
