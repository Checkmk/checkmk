#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
from typing import Any

import cmk.utils.plugin_registry
import cmk.utils.store as store

from cmk.gui.userdb import clear_user_connection_cache, user_connector_registry

UserConnectionSpec = dict[str, Any]  # TODO: Minimum should be a TypedDict


def _multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# .
#   .--ConnectorCfg--------------------------------------------------------.
#   |    ____                            _              ____  __           |
#   |   / ___|___  _ __  _ __   ___  ___| |_ ___  _ __ / ___|/ _| __ _     |
#   |  | |   / _ \| '_ \| '_ \ / _ \/ __| __/ _ \| '__| |   | |_ / _` |    |
#   |  | |__| (_) | | | | | | |  __/ (__| || (_) | |  | |___|  _| (_| |    |
#   |   \____\___/|_| |_|_| |_|\___|\___|\__\___/|_|   \____|_|  \__, |    |
#   |                                                            |___/     |
#   +----------------------------------------------------------------------+
#   | The user can enable and configure a list of user connectors which    |
#   | are then used by the userdb to fetch user / group information from   |
#   | external sources like LDAP servers.                                  |
#   '----------------------------------------------------------------------'


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
