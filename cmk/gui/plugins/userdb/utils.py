#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union

from livestatus import SiteId

import cmk.utils.plugin_registry
import cmk.utils.store as store
from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

from cmk.gui.config import builtin_role_ids
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser, save_user_file, user
from cmk.gui.sites import get_site_config, is_wato_slave_site, site_is_local
from cmk.gui.type_defs import UserSpec
from cmk.gui.utils import is_allowed_url

# count this up, if new user attributes are used or old are marked as
# incompatible
USER_SCHEME_SERIAL = 0

RoleSpec = Dict[str, Any]  # TODO: Improve this type
Roles = Dict[str, RoleSpec]  # TODO: Improve this type
UserConnectionSpec = Dict[str, Any]  # TODO: Improve this type
UserSyncConfig = Optional[str]
CheckCredentialsResult = Union[UserId, None, Literal[False]]


def load_cached_profile(user_id: UserId) -> Optional[UserSpec]:
    usr = LoggedInUser(user_id) if user_id != user.id else user
    return usr.load_file("cached_profile", None)


def save_cached_profile(user_id: UserId, cached_profile: UserSpec) -> None:
    save_user_file("cached_profile", cached_profile, user_id=user_id)


def _multisite_dir() -> str:
    return cmk.utils.paths.default_config_dir + "/multisite.d/wato/"


def _root_dir() -> str:
    return cmk.utils.paths.check_mk_config_dir + "/wato/"


def release_users_lock() -> None:
    store.release_lock(_root_dir() + "contacts.mk")


def user_sync_config() -> UserSyncConfig:
    # use global option as default for reading legacy options and on remote site
    # for reading the value set by the WATO master site
    default_cfg = user_sync_default_config(omd_site())
    return get_site_config(omd_site()).get("user_sync", default_cfg)


# Legacy option config.userdb_automatic_sync defaulted to "master".
# Can be: None: (no sync), "all": all sites sync, "master": only master site sync
# Take that option into account for compatibility reasons.
# For remote sites in distributed setups, the default is to do no sync.
def user_sync_default_config(site_name: SiteId) -> UserSyncConfig:
    global_user_sync = _transform_userdb_automatic_sync(config.userdb_automatic_sync)
    if global_user_sync == "master":
        if site_is_local(site_name) and not is_wato_slave_site():
            user_sync_default: UserSyncConfig = "all"
        else:
            user_sync_default = None
    else:
        user_sync_default = global_user_sync

    return user_sync_default


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


def new_user_template(connection_id: str) -> UserSpec:
    new_user = UserSpec(
        serial=0,
        connector=connection_id,
    )

    # Apply the default user profile
    new_user.update(config.default_user_profile)
    return new_user


def add_internal_attributes(usr: UserSpec) -> int:
    return usr.setdefault("user_scheme_serial", USER_SCHEME_SERIAL)


def show_mode_choices() -> List[Tuple[Optional[str], str]]:
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
def get_connection(connection_id: Optional[str]) -> "Optional[UserConnector]":
    """Returns the connection object of the requested connection id

    This function maintains a cache that for a single connection_id only one object per request is
    created."""
    connections_with_id = [c for cid, c in _all_connections() if cid == connection_id]
    return connections_with_id[0] if connections_with_id else None


def clear_user_connection_cache() -> None:
    get_connection.cache_clear()


def active_connections() -> "List[Tuple[str, UserConnector]]":
    enabled_configs = [cfg for cfg in _get_connection_configs() if not cfg["disabled"]]  #
    return [
        (connection_id, connection)  #
        for connection_id, connection in _get_connections_for(enabled_configs)
        if connection.is_enabled()
    ]


def connection_choices() -> List[Tuple[str, str]]:
    return sorted(
        [
            (connection_id, "%s (%s)" % (connection_id, connection.type()))
            for connection_id, connection in _all_connections()
            if connection.type() == "ldap"
        ],
        key=lambda id_and_description: id_and_description[1],
    )


def _all_connections() -> "List[Tuple[str, UserConnector]]":
    return _get_connections_for(_get_connection_configs())


def _get_connections_for(configs: List[Dict[str, Any]]) -> "List[Tuple[str, UserConnector]]":
    return [(cfg["id"], user_connector_registry[cfg["type"]](cfg)) for cfg in configs]


def _get_connection_configs() -> List[Dict[str, Any]]:
    # The htpasswd connector is enabled by default and always executed first.
    return [_HTPASSWD_CONNECTION] + config.user_connections


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


def load_connection_config(lock: bool = False) -> List[UserConnectionSpec]:
    filename = os.path.join(_multisite_dir(), "user_connections.mk")
    return store.load_from_mk_file(filename, "user_connections", default=[], lock=lock)


def save_connection_config(
    connections: List[UserConnectionSpec], base_dir: Optional[str] = None
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
    config.roles.update(roles)

    return roles


def _get_builtin_roles() -> Roles:
    """Returns a role dictionary containing the bultin default roles"""
    builtin_role_names = {
        "admin": _("Administrator"),
        "user": _("Normal monitoring user"),
        "guest": _("Guest user"),
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


class UserConnector(abc.ABC):
    def __init__(self, cfg) -> None:
        self._config = cfg

    @classmethod
    @abc.abstractmethod
    def type(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls):
        """The string representing this connector to humans"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def short_title(cls):
        raise NotImplementedError()

    @classmethod
    def config_changed(cls):
        return

    #
    # USERDB API METHODS
    #

    @abc.abstractmethod
    def is_enabled(self):
        raise NotImplementedError()

    # Optional: Hook function can be registered here to be executed
    # to validate a login issued by a user.
    # Gets parameters: username, password
    # Has to return either:
    #     '<user_id>' -> Login succeeded
    #     False       -> Login failed
    #     None        -> Unknown user
    @abc.abstractmethod
    def check_credentials(self, user_id, password) -> CheckCredentialsResult:
        return None

    # Optional: Hook function can be registered here to be executed
    # to synchronize all users.
    def do_sync(self, add_to_changelog, only_username, load_users_func, save_users_func):
        pass

    # Optional: Tells whether or not the synchronization (using do_sync()
    # method) is needed.
    def sync_is_needed(self):
        return False

    # Optional: Hook function can be registered here to be xecuted
    # to save all users.
    def save_users(self, users):
        pass

    # List of user attributes locked for all users attached to this
    # connection. Those locked attributes are read-only in WATO.
    def locked_attributes(self) -> List[str]:
        return []

    def multisite_attributes(self) -> List[str]:
        return []

    def non_contact_attributes(self) -> List[str]:
        return []


# .
#   .--UserAttribute-------------------------------------------------------.
#   |     _   _                _   _   _        _ _           _            |
#   |    | | | |___  ___ _ __ / \ | |_| |_ _ __(_) |__  _   _| |_ ___      |
#   |    | | | / __|/ _ \ '__/ _ \| __| __| '__| | '_ \| | | | __/ _ \     |
#   |    | |_| \__ \  __/ | / ___ \ |_| |_| |  | | |_) | |_| | ||  __/     |
#   |     \___/|___/\___|_|/_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Base class for user attributes                                       |
#   '----------------------------------------------------------------------'


class UserAttribute(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def topic(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def valuespec(self):
        raise NotImplementedError()

    def from_config(self) -> bool:
        return False

    def user_editable(self) -> bool:
        return True

    def permission(self) -> Optional[str]:
        return None

    def show_in_table(self) -> bool:
        return False

    def add_custom_macro(self) -> bool:
        return False

    def domain(self) -> str:
        return "multisite"


# .
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'


class UserConnectorRegistry(cmk.utils.plugin_registry.Registry[Type[UserConnector]]):
    """The management object for all available user connector classes.

    Have a look at the base class for details."""

    def plugin_name(self, instance):
        return instance.type()


user_connector_registry = UserConnectorRegistry()


class UserAttributeRegistry(cmk.utils.plugin_registry.Registry[Type[UserAttribute]]):
    """The management object for all available user attributes.
    Have a look at the base class for details."""

    def plugin_name(self, instance):
        return instance.name()


user_attribute_registry = UserAttributeRegistry()


def get_user_attributes() -> List[Tuple[str, UserAttribute]]:
    return [(name, attribute_class()) for name, attribute_class in user_attribute_registry.items()]


def get_user_attributes_by_topic() -> Dict[str, List[Tuple[str, UserAttribute]]]:
    topics: Dict[str, List[Tuple[str, UserAttribute]]] = {}
    for name, attr_class in user_attribute_registry.items():
        topic = attr_class().topic()
        topics.setdefault(topic, []).append((name, attr_class()))

    return topics
