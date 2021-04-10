#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Type, List

from six import ensure_str

import cmk.utils.plugin_registry


class PermissionSection(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def name(self) -> str:
        """The identity of a permission section.
        One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """Display name representing the section"""
        raise NotImplementedError()

    @property
    def sort_index(self) -> int:
        """Number to sort the sections with"""
        return 50

    # TODO: Is this still needed?
    @property
    def do_sort(self) -> bool:
        """Whether or not to sort the permissions by title in this section"""
        return False


class PermissionSectionRegistry(cmk.utils.plugin_registry.Registry[Type[PermissionSection]]):
    def plugin_name(self, instance):
        return instance().name

    def get_sorted_sections(self):
        return sorted([s() for s in self.values()], key=lambda s: (s.sort_index, s.title))


permission_section_registry = PermissionSectionRegistry()


class Permission(metaclass=abc.ABCMeta):
    _sort_index = 0

    def __init__(self, section: Type[PermissionSection], name: str, title: str, description: str,
                 defaults: List[str]) -> None:
        self._section = section
        self._name = name
        self._title = title
        self._description = description
        self._defaults = defaults
        self._sort_index = 0

    @property
    def section(self) -> Type[PermissionSection]:
        return self._section

    @property
    def permission_name(self) -> str:
        """The identity of a permission (without it's section identity).
        One word, may contain alpha numeric characters"""
        return self._name

    @property
    def title(self) -> str:
        """Display name representing the permission"""
        return self._title

    @property
    def description(self) -> str:
        """Text to explain the purpose of this permission"""
        return self._description

    @property
    def defaults(self) -> List[str]:
        """List of role IDs that have this permission by default"""
        return self._defaults

    @property
    def name(self) -> str:
        """The full identity of a permission (including the section identity)."""
        return ".".join((self.section().name, self.permission_name))

    @property
    def sort_index(self) -> int:
        """Number to sort the permission with"""
        return self._sort_index

    @sort_index.setter
    def sort_index(self, value: int) -> None:
        self._sort_index = value


class PermissionRegistry(cmk.utils.plugin_registry.Registry[Permission]):
    def __init__(self):
        super(PermissionRegistry, self).__init__()
        # TODO: Better make the sorting explicit in the future
        # used as auto incrementing counter to numerate the permissions in
        # the order they have been added.
        self._index_counter = 0

    def plugin_name(self, instance):
        return instance.name

    def registration_hook(self, instance):
        instance._sort_index = self._index_counter
        self._index_counter += 1

    def get_sorted_permissions(self, section):
        """Returns the sorted permissions of a section respecting the sorting config of the section"""
        permissions = [p for p in self.values() if p.section == section.__class__]

        if section.do_sort:
            return sorted(permissions, key=lambda p: (p.title, p.sort_index))
        return sorted(permissions, key=lambda p: p.sort_index)


permission_registry = PermissionRegistry()


# Kept for compatibility with pre 1.6 GUI plugins
def declare_permission_section(name, title, prio=50, do_sort=False):
    cls = type("LegacyPermissionSection%s" % name.title(), (PermissionSection,), {
        "name": name,
        "title": title,
        "sort_index": prio,
        "do_sort": do_sort,
    })
    permission_section_registry.register(cls)


# Kept for compatibility with pre 1.6 GUI plugins
# Some dynamically registered permissions still use this
def declare_permission(name, title, description, defaults):
    if not isinstance(name, str):
        name = ensure_str(name, encoding="ascii")

    section_name, permission_name = name.split(".", 1)

    permission_registry.register(
        Permission(
            section=permission_section_registry[section_name],
            name=permission_name,
            title=title,
            description=description,
            defaults=defaults,
        ))
