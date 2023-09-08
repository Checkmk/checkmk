#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import os
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Literal

import cmk.utils.plugin_registry
import cmk.utils.store as store
from cmk.utils.crypto.password import Password
from cmk.utils.urls import is_allowed_url
from cmk.utils.user import UserId

from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.type_defs import Users, UserSpec

RoleSpec = dict[str, Any]  # TODO: Improve this type
Roles = dict[str, RoleSpec]  # TODO: Improve this type
UserConnectionSpec = dict[str, Any]  # TODO: Minimum should be a TypedDict
CheckCredentialsResult = UserId | None | Literal[False]


def _multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


# Old vs:
# ListChoice(
#    title = _('Automatic User Synchronization'),
#    help  = _('By default the users are synchronized automatically in several situations. '
#              'The sync is started when opening the "Users" page in configuration and '
#              'during each page rendering. Each connector can then specify if it wants to perform '
#              'any actions. For example the LDAP connector will start the sync once the cached user '
#              'information are too old.'),
#    default_value = [ 'wato_users', 'page', 'wato_pre_activate_changes', 'wato_snapshot_pushed' ],
#    choices       = [
#        ('page',                      _('During regular page processing')),
#        ('wato_users',                _('When opening the users\' configuration page')),
#        ('wato_pre_activate_changes', _('Before activating the changed configuration')),
#        ('wato_snapshot_pushed',      _('On a remote site, when it receives a new configuration')),
#    ],
#    allow_empty   = True,
# ),
def _transform_userdb_automatic_sync(val):
    if val == []:
        # legacy compat - disabled
        return None

    if isinstance(val, list) and val:
        # legacy compat - all connections
        return "all"

    return val


def show_mode_choices() -> list[tuple[str | None, str]]:
    return [
        ("default_show_less", _("Default to show less")),
        ("default_show_more", _("Default to show more")),
        ("enforce_show_more", _("Enforce show more")),
    ]


def validate_start_url(value: str, varprefix: str) -> None:
    if not is_allowed_url(value):
        raise MKUserError(
            varprefix,
            _(
                "The given value is not allowed. You may only configure "
                "relative URLs like <tt>dashboard.py?name=my_dashboard</tt>."
            ),
        )


#   .--Connections---------------------------------------------------------.
#   |        ____                            _   _                         |
#   |       / ___|___  _ __  _ __   ___  ___| |_(_) ___  _ __  ___         |
#   |      | |   / _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \/ __|        |
#   |      | |__| (_) | | | | | | |  __/ (__| |_| | (_) | | | \__ \        |
#   |       \____\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Managing the configured connections                                  |
#   '----------------------------------------------------------------------'


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
    # The htpasswd connector is enabled by default and always executed first.
    return [_HTPASSWD_CONNECTION] + active_config.user_connections


_HTPASSWD_CONNECTION = {
    "type": "htpasswd",
    "id": "htpasswd",
    "disabled": False,
}

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
    filename = os.path.join(_multisite_dir(), "user_connections.mk")
    return store.load_from_mk_file(filename, "user_connections", default=[], lock=lock)


def save_connection_config(
    connections: list[UserConnectionSpec], base_dir: str | None = None
) -> None:
    if not base_dir:
        base_dir = _multisite_dir()
    store.mkdir(base_dir)
    store.save_to_mk_file(
        os.path.join(base_dir, "user_connections.mk"), "user_connections", connections
    )

    for connector_class in user_connector_registry.values():
        connector_class.config_changed()

    clear_user_connection_cache()


# .
#   .-Roles----------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def load_roles() -> Roles:
    roles = store.load_from_mk_file(
        os.path.join(_multisite_dir(), "roles.mk"),
        "roles",
        default=_get_builtin_roles(),
    )

    # Make sure that "general." is prefixed to the general permissions
    # (due to a code change that converted "use" into "general.use", etc.
    # TODO: Can't we drop this? This seems to be from very early days of the GUI
    for role in roles.values():
        for pname, pvalue in role["permissions"].items():
            if "." not in pname:
                del role["permissions"][pname]
                role["permissions"]["general." + pname] = pvalue

    # Reflect the data in the roles dict kept in the config module needed
    # for instant changes in current page while saving modified roles.
    # Otherwise the hooks would work with old data when using helper
    # functions from the config module
    # TODO: load_roles() should not update global structures
    active_config.roles.update(roles)

    return roles


def _get_builtin_roles() -> Roles:
    """Returns a role dictionary containing the bultin default roles"""
    builtin_role_names = {
        "admin": _("Administrator"),
        "user": _("Normal monitoring user"),
        "guest": _("Guest user"),
        "agent_registration": _("Agent registration user"),
    }
    return {
        rid: {
            "alias": builtin_role_names.get(rid, rid),
            "permissions": {},  # use default everywhere
            "builtin": True,
        }
        for rid in builtin_role_ids
    }


# .
#   .--ConnectorAPI--------------------------------------------------------.
#   |     ____                            _              _    ____ ___     |
#   |    / ___|___  _ __  _ __   ___  ___| |_ ___  _ __ / \  |  _ \_ _|    |
#   |   | |   / _ \| '_ \| '_ \ / _ \/ __| __/ _ \| '__/ _ \ | |_) | |     |
#   |   | |__| (_) | | | | | | |  __/ (__| || (_) | | / ___ \|  __/| |     |
#   |    \____\___/|_| |_|_| |_|\___|\___|\__\___/|_|/_/   \_\_|  |___|    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Implements the base class for User Connector classes. It implements  |
#   | basic mechanisms and default methods which might/should be           |
#   | overridden by the specific connector classes.                        |
#   '----------------------------------------------------------------------'


class ConnectorType:
    # TODO: should be improved to be an enum
    SAML2 = "saml2"
    LDAP = "ldap"
    HTPASSWD = "htpasswd"
    OAUTH2 = "oauth2"


class UserConnector(abc.ABC):
    def __init__(self, cfg) -> None:  # type: ignore[no-untyped-def]
        self._config = cfg

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        """The string representing this connector to humans"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def id(self) -> str:
        """The unique identifier of the connection"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def short_title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def config_changed(cls) -> None:
        return

    #
    # USERDB API METHODS
    #

    @abc.abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError()

    # Optional: Hook function can be registered here to be executed
    # to validate a login issued by a user.
    # Gets parameters: username, password
    # Has to return either:
    #     '<user_id>' -> Login succeeded
    #     False       -> Login failed
    #     None        -> Unknown user
    def check_credentials(self, user_id: UserId, password: Password) -> CheckCredentialsResult:
        return None

    # Optional: Hook function can be registered here to be executed
    # to synchronize all users.
    def do_sync(
        self,
        *,
        add_to_changelog: bool,
        only_username: UserId | None,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
    ) -> None:
        pass

    # Optional: Tells whether or not the synchronization (using do_sync()
    # method) is needed.
    def sync_is_needed(self) -> bool:
        return False

    # Optional: Hook function can be registered here to be xecuted
    # to save all users.
    def save_users(self, users: dict[UserId, UserSpec]) -> None:
        pass

    # List of user attributes locked for all users attached to this
    # connection. Those locked attributes are read-only in Setup.
    def locked_attributes(self) -> Sequence[str]:
        return []

    def multisite_attributes(self) -> Sequence[str]:
        return []

    def non_contact_attributes(self) -> Sequence[str]:
        return []


# .
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'


class UserConnectorRegistry(cmk.utils.plugin_registry.Registry[type[UserConnector]]):
    """The management object for all available user connector classes.

    Have a look at the base class for details."""

    def plugin_name(self, instance):
        return instance.type()


user_connector_registry = UserConnectorRegistry()
