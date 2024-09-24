#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Callable, Sequence
from typing import Any

import cmk.utils.plugin_registry
import cmk.utils.store as store

from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize

from ._connector import ConnectorType, user_connector_registry, UserConnector

UserConnectionSpec = dict[str, Any]  # TODO: Minimum should be a TypedDict


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


def _get_connections_for(
    configs: list[dict[str, Any]],
) -> list[tuple[str, UserConnector]]:
    return [(cfg["id"], user_connector_registry[cfg["type"]](cfg)) for cfg in configs]


def _get_connection_configs() -> list[dict[str, Any]]:
    return builtin_connections + active_config.user_connections


_HTPASSWD_CONNECTION = {
    "type": "htpasswd",
    "id": "htpasswd",
    "disabled": False,
}
# The htpasswd connector is enabled by default and always executed first.
# NOTE: This list may be appended to in edition specific registration functions.
builtin_connections = [_HTPASSWD_CONNECTION]


# The saved configuration for user connections is a bit inconsistent, let's fix
# this here once and for all.
def fix_user_connections() -> None:
    for cfg in active_config.user_connections:
        # Although our current configuration always seems to have a 'disabled'
        # entry, this might not have always been the case.
        cfg.setdefault("disabled", False)
        # Only migrated configurations have a 'type' entry, all others are
        # implictly LDAP connections.
        cfg.setdefault("type", "ldap")


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


def _multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


def load_connection_config(lock: bool = False) -> list[UserConnectionSpec]:
    """Load the configured connections for the Setup

    Note:
        This function should only be used in the Setup context, when configuring
        the connections. During UI rendering, `active_config.user_connections` must
        be used.
    """
    filename = os.path.join(_multisite_dir(), "user_connections.mk")
    return store.load_from_mk_file(filename, "user_connections", default=[], lock=lock)


def save_connection_config(
    connections: list[UserConnectionSpec], base_dir: str | None = None
) -> None:
    """Save the connections for the Setup

    Note:
        This function should only be used in the Setup context, when configuring
        the connections. During UI rendering, `active_config.user_connections` must
        be used.
    """
    if not base_dir:
        base_dir = _multisite_dir()
    store.mkdir(base_dir)
    store.save_to_mk_file(
        os.path.join(base_dir, "user_connections.mk"), "user_connections", connections
    )

    for connector_class in user_connector_registry.values():
        connector_class.config_changed()

    clear_user_connection_cache()
