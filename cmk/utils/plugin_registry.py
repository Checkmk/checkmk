#!/usr/bin/python
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
import six

# TODO: Refactor all plugins to one way of telling the registry it's name.
#       for example let all use a static/class method .name().
#       We could standardize this by making all plugin classes inherit
#       from a plugin base class instead of "object".

# TODO: Decide which base class to implement
# (https://docs.python.org/2/library/collections.html) and cleanup


class ABCRegistry(six.with_metaclass(abc.ABCMeta, object)):
    """The management object for all available plugins of a component.

    The snapins are loaded by importing cmk.gui.plugins.[component]. These plugins
    contain subclasses of the cmk.gui.plugins.PluginBase (e.g. SidebarSnpain) class.

    Entries are registered with this registry using register(), typically via decoration.

    """
    def __init__(self):
        super(ABCRegistry, self).__init__()
        self._entries = {}

    # TODO: Make staticmethod (But abc.abstractstaticmethod not available. How to make this possible?)
    @abc.abstractmethod
    def plugin_base_class(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def plugin_name(self, plugin_class):
        raise NotImplementedError()

    def registration_hook(self, plugin_class):
        pass

    @abc.abstractmethod
    def register(self, plugin_class):
        raise NotImplementedError()

    def __contains__(self, text):
        return text in self._entries

    def __delitem__(self, key):
        del self._entries[key]

    def __getitem__(self, key):
        return self._entries[key]

    def __len__(self):
        return len(self._entries)

    def values(self):
        return self._entries.values()

    def items(self):
        return self._entries.items()

    def keys(self):
        return self._entries.keys()

    def get(self, key, deflt=None):
        return self._entries.get(key, deflt)


class ClassRegistry(ABCRegistry):
    def register(self, plugin_class):
        """Register a class with the registry, can be used as a decorator"""
        if not issubclass(plugin_class, self.plugin_base_class()):
            raise TypeError('%s is not a subclass of %s' %
                            (plugin_class.__name__, self.plugin_base_class().__name__))
        self.registration_hook(plugin_class)
        self._entries[self.plugin_name(plugin_class)] = plugin_class
        return plugin_class


class InstanceRegistry(ABCRegistry):
    def register(self, instance):  # pylint: disable=arguments-differ
        self.registration_hook(instance)
        self._entries[self.plugin_name(instance)] = instance
        return instance

    def plugin_name(self, instance):  # pylint: disable=arguments-differ
        return instance.name
