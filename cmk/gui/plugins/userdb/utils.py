#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
from typing import List, Optional  # pylint: disable=unused-import
import six

import cmk.utils.plugin_registry

#.
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


class UserConnector(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self, config):
        super(UserConnector, self).__init__()
        self._config = config

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

    @classmethod
    def migrate_config(cls):
        pass

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
    def check_credentials(self, user_id, password):
        return None

    # Optional: Hook function can be registered here to be executed
    # to synchronize all users.
    def do_sync(self, add_to_changelog, only_username):
        pass

    # Optional: Tells whether or not the synchronization (using do_sync()
    # method) is needed.
    def sync_is_needed(self):
        return False

    # Optional: Tells whether or not the given user is currently
    # locked which would mean that he is not allowed to login.
    def is_locked(self, user_id):
        return False

    # Optional: Hook function can be registered here to be xecuted
    # to save all users.
    def save_users(self, users):
        pass

    # List of user attributes locked for all users attached to this
    # connection. Those locked attributes are read-only in WATO.
    def locked_attributes(self):
        # type: () -> List[str]
        return []

    def multisite_attributes(self):
        # type: () -> List[str]
        return []

    def non_contact_attributes(self):
        # type: () -> List[str]
        return []


#.
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


class UserAttribute(six.with_metaclass(abc.ABCMeta, object)):
    @classmethod
    @abc.abstractmethod
    def name(cls):
        # type: () -> bytes
        raise NotImplementedError()

    @abc.abstractmethod
    def topic(self):
        # type: () -> bytes
        raise NotImplementedError()

    @abc.abstractmethod
    def valuespec(self):
        raise NotImplementedError()

    def from_config(self):
        # type: () -> bool
        return False

    def user_editable(self):
        # type: () -> bool
        return True

    def permission(self):
        # type: () -> Optional[bytes]
        return None

    def show_in_table(self):
        # type: () -> bool
        return False

    def add_custom_macro(self):
        # type: () -> bool
        return False

    def domain(self):
        # type: () -> bytes
        return "multisite"


#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'


class UserConnectorRegistry(cmk.utils.plugin_registry.ClassRegistry):
    """The management object for all available user connector classes.

    Have a look at the base class for details."""
    def plugin_base_class(self):
        return UserConnector

    def plugin_name(self, plugin_class):
        return plugin_class.type()

    def registration_hook(self, plugin_class):
        plugin_class.migrate_config()


user_connector_registry = UserConnectorRegistry()


class UserAttributeRegistry(cmk.utils.plugin_registry.ClassRegistry):
    """The management object for all available user attributes.
    Have a look at the base class for details."""
    def plugin_base_class(self):
        return UserAttribute

    def plugin_name(self, plugin_class):
        return plugin_class.name()


user_attribute_registry = UserAttributeRegistry()


def get_user_attributes():
    return [(name, attribute_class()) for name, attribute_class in user_attribute_registry.items()]
