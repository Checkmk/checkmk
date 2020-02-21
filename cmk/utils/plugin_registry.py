#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Tuple, Type, Dict, Any  # pylint: disable=unused-import

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
        # type: () -> None
        super(ABCRegistry, self).__init__()
        self._entries = {}  # type: Dict[str, Any]

    # TODO: Make staticmethod (But abc.abstractstaticmethod not available. How to make this possible?)
    @abc.abstractmethod
    def plugin_base_class(self):
        # type: () -> Type
        raise NotImplementedError()

    @abc.abstractmethod
    def plugin_name(self, plugin_class):
        # type: (Type) -> str
        raise NotImplementedError()

    def registration_hook(self, plugin_class):
        # type: (Type) -> None
        pass

    @abc.abstractmethod
    def register(self, plugin_class):
        # type: (Type) -> Type
        raise NotImplementedError()

    def __contains__(self, text):
        # type: (str) -> bool
        return text in self._entries

    def __delitem__(self, key):
        # type: (str) -> None
        del self._entries[key]

    def __getitem__(self, key):
        # type: (str) -> Any
        return self._entries[key]

    def __len__(self):
        # type: () -> int
        return len(self._entries)

    def values(self):
        # type: () -> Iterable[Any]
        return self._entries.values()

    def items(self):
        # type: () -> Iterable[Tuple[str, Any]]
        return self._entries.items()

    def keys(self):
        # type: () -> Iterable[str]
        return self._entries.keys()

    def get(self, key, deflt=None):
        # type: (str, Any) -> Any
        return self._entries.get(key, deflt)


class ClassRegistry(ABCRegistry):
    def register(self, plugin_class):
        # type: (Type) -> Type
        """Register a class with the registry, can be used as a decorator"""
        if not issubclass(plugin_class, self.plugin_base_class()):
            raise TypeError('%s is not a subclass of %s' %
                            (plugin_class.__name__, self.plugin_base_class().__name__))
        self.registration_hook(plugin_class)
        self._entries[self.plugin_name(plugin_class)] = plugin_class
        return plugin_class


class InstanceRegistry(ABCRegistry):
    def register(self, instance):  # pylint: disable=arguments-differ
        # type: (Any) -> Any
        self.registration_hook(instance)
        self._entries[self.plugin_name(instance)] = instance
        return instance

    def plugin_name(self, instance):  # pylint: disable=arguments-differ
        # type: (Any) -> str
        return instance.name
