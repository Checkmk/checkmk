#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import abstractmethod
from typing import Dict, Iterator, Mapping, Type, TypeVar

_VT = TypeVar("_VT")

# TODO: Refactor all plugins to one way of telling the registry it's name.
#       for example let all use a static/class method .name().
#       We could standardize this by making all plugin classes inherit
#       from a plugin base class instead of "object".


class Registry(Mapping[str, _VT]):
    """An abstract registry that stores objects of a given class.

    To create a registry inherit from ``Registry[A]`` where ``A`` is the class
    of the objects that are stored in the registry. Although it is not
    recommended classes can be stored inside registries as well. To create a
    class registry you have to derive from ``Registry[Type[A]]``.

    Objects can be added or removed with the register and unregister methods.

    Objects can be retrieved from the registry with a dictionary like syntax.

    Examples:

        >>> from cmk.utils.plugin_registry import Registry
        >>> class A:
        ...     def __init__(self, name: str):
        ...         self.name = name
        >>> class MyRegistry(Registry[A]):
        ...     def plugin_name(self, instance: A) -> str:
        ...         return instance.name
        >>> my_registry = MyRegistry()
        >>> my_a = A('my_a')
        >>> _ = my_registry.register(my_a)
        >>> assert my_registry['my_a'] == my_a

    """

    def __init__(self) -> None:
        super().__init__()
        self._entries: Dict[str, _VT] = {}

    @abstractmethod
    def plugin_name(self, instance: _VT) -> str:
        raise NotImplementedError()

    def registration_hook(self, instance: _VT) -> None:
        pass

    def register(self, instance: _VT) -> _VT:
        self.registration_hook(instance)
        self._entries[self.plugin_name(instance)] = instance
        return instance

    def register_instance(self, cls: Type[_VT]) -> Type[_VT]:
        """Decorate a class to create an instance of the class and register it to the object registry"""
        self.register(cls())
        return cls

    def unregister(self, name: str) -> None:
        del self._entries[name]

    def __getitem__(self, key: str) -> _VT:
        return self._entries.__getitem__(key)

    def __len__(self) -> int:
        return self._entries.__len__()

    def __iter__(self) -> Iterator[str]:
        return self._entries.__iter__()
