#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import abstractmethod
from typing import Any, Dict, Mapping, Type, TypeVar

_VT = TypeVar('_VT')


# TODO: Refactor all plugins to one way of telling the registry it's name.
#       for example let all use a static/class method .name().
#       We could standardize this by making all plugin classes inherit
#       from a plugin base class instead of "object".
class ABCRegistry(Mapping[str, _VT]):
    """The management object for all available plugins of a component.

    The snapins are loaded by importing cmk.gui.plugins.[component]. These plugins
    contain subclasses of the cmk.gui.plugins.PluginBase (e.g. SidebarSnpain) class.

    Entries are registered with this registry using register(), typically via decoration.

    """
    def __init__(self):
        # type: () -> None
        super(ABCRegistry, self).__init__()
        self._entries = {}  # type: Dict[str, _VT]

    # TODO: Make staticmethod (But abc.abstractstaticmethod not available. How to make this possible?)
    @abstractmethod
    def plugin_base_class(self):
        # type: () -> Type
        raise NotImplementedError()

    @abstractmethod
    def plugin_name(self, plugin_class):
        # type: (Type) -> str
        raise NotImplementedError()

    def registration_hook(self, plugin_class):
        # type: (Type) -> None
        pass

    @abstractmethod
    def register(self, plugin_class):
        # type: (Type) -> Type
        raise NotImplementedError()

    def unregister(self, name):
        # type: (str) -> None
        del self._entries[name]

    def __getitem__(self, key):
        return self._entries.__getitem__(key)

    def __len__(self):
        return self._entries.__len__()

    def __iter__(self):
        return self._entries.__iter__()


# Abstract methods:
#
# def plugin_base_class(self) -> Type
# def plugin_name(self, plugin_class: Type) -> Type
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


# Abstract methods:
#
# def plugin_base_class(self) -> Type
class InstanceRegistry(ABCRegistry):
    def register(self, instance):  # pylint: disable=arguments-differ
        # type: (Any) -> Any
        if not isinstance(instance, self.plugin_base_class()):
            raise ValueError('%r is not an instance of %s' %
                             (instance, self.plugin_base_class().__name__))
        self.registration_hook(instance)
        self._entries[self.plugin_name(instance)] = instance
        return instance

    def plugin_name(self, instance):  # pylint: disable=arguments-differ
        # type: (Any) -> str
        return instance.name
