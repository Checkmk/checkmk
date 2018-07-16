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

# TODO: We decided to change this plugin registry from automatically finding
# it's childs to explicit registration.
# TODO: In the moment we have this, we can drop the auto_register stuff.

class Registry(object):
    """The management object for all available plugins of a component.

    The snapins are loaded by importing cmk.gui.plugins.[component]. These plugins
    contain subclasses of the cmk.gui.plugins.PluginBase (e.g. SidebarSnpain) class.

    Entries are registered with this registry using either the register_plugin()
    method or the Registry.register() decorator.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        super(Registry, self).__init__()
        self._entries = {}


    # TODO: Make staticmethod (But abc.abstractstaticmethod not available. How to make this possible?)
    @abc.abstractmethod
    def plugin_base_class(self):
        raise NotImplementedError()


    def load_plugins(self):
        self._entries.clear()

        def _all_subclasses_of(base_class):
            l = []
            for plugin_class in base_class.__subclasses__(): # pylint: disable=no-member
                l += _all_subclasses_of(plugin_class)
                l.append(plugin_class)
            return l

        for plugin_class in _all_subclasses_of(self.plugin_base_class()):
            if plugin_class.__subclasses__(): # pylint: disable=no-member
                continue # Only use leaf classes

            # TODO: Create one base class for all plugin classes to provide a default for this
            if hasattr(plugin_class, "auto_register") and not plugin_class.auto_register():
                return

            self.register(self._instanciate(plugin_class))


    @abc.abstractmethod
    def _instanciate(self, cls):
        raise NotImplementedError()


    @abc.abstractmethod
    def register(self, plugin_class):
        """Decorator to register a class with the registry"""
        self._register(plugin_class)


    @abc.abstractmethod
    def register_plugin(self, plugin_class):
        """Method for registering a plugin with the registry.

        Result is equal to use the register() decorator"""
        self._register(plugin_class)


    @abc.abstractmethod
    def _register(self, plugin_class):
        raise NotImplementedError()


    def __contains__(self, text):
        return text in self._entries


    def __delitem__(self, key):
        del self._entries[key]


    def __getitem__(self, key):
        return self._entries[key]


    def values(self):
        return self._entries.values()


    def items(self):
        return self._entries.items()


    def keys(self):
        return self._entries.keys()


    def get(self, key, deflt=None):
        return self._entries.get(key, deflt)



class ClassRegistry(Registry):
    def _instanciate(self, cls):
        return cls



class ObjectRegistry(Registry):
    def _instanciate(self, cls):
        return cls()
