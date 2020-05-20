#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Text, Type, List  # pylint: disable=unused-import
import six

import cmk.utils.plugin_registry


class PermissionSection(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractproperty
    def name(self):
        # type: () -> str
        """The identity of a permission section.
        One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Display name representing the section"""
        raise NotImplementedError()

    @property
    def sort_index(self):
        # type: () -> int
        """Number to sort the sections with"""
        return 50

    # TODO: Is this still needed?
    @property
    def do_sort(self):
        # type: () -> bool
        """Whether or not to sort the permissions by title in this section"""
        return False


class PermissionSectionRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return PermissionSection

    def plugin_name(self, plugin_class):
        return plugin_class().name

    def get_sorted_sections(self):
        return sorted([s() for s in self.values()], key=lambda s: (s.sort_index, s.title))


permission_section_registry = PermissionSectionRegistry()


class Permission(six.with_metaclass(abc.ABCMeta, object)):
    _sort_index = 0

    @abc.abstractproperty
    def section(self):
        # type: () -> Type[PermissionSection]
        raise NotImplementedError()

    @abc.abstractproperty
    def permission_name(self):
        # type: () -> str
        """The identity of a permission (without it's section identity).
        One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Display name representing the permission"""
        raise NotImplementedError()

    @abc.abstractproperty
    def description(self):
        # type: () -> Text
        """Text to explain the purpose of this permission"""
        raise NotImplementedError()

    @abc.abstractproperty
    def defaults(self):
        # type: () -> List[str]
        """List of role IDs that have this permission by default"""
        raise NotImplementedError()

    @property
    def name(self):
        # type: () -> str
        """The full identity of a permission (including the section identity)."""
        return ".".join((self.section().name, self.permission_name))

    @property
    def sort_index(self):
        # type: () -> int
        """Number to sort the permission with"""
        return self._sort_index


class PermissionRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def __init__(self):
        super(PermissionRegistry, self).__init__()
        # TODO: Better make the sorting explicit in the future
        # used as auto incrementing counter to numerate the permissions in
        # the order they have been added.
        self._index_counter = 0

    def plugin_base_class(self):
        return Permission

    def plugin_name(self, plugin_class):
        return plugin_class().name

    def registration_hook(self, plugin_class):
        plugin_class._sort_index = self._index_counter
        self._index_counter += 1

    def get_sorted_permissions(self, section):
        """Returns the sorted permissions of a section respecting the sorting config of the section"""
        permissions = [
            p for p in [p_class() for p_class in self.values()] if p.section == section.__class__
        ]

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
        name = six.ensure_str(name, encoding="ascii")

    section_name, permission_name = name.split(".", 1)

    cls = type(
        "LegacyPermission%s%s" % (section_name.title(), permission_name.title()), (Permission,), {
            "_section_name": section_name,
            "section": property(lambda s: permission_section_registry[s._section_name]),
            "permission_name": permission_name,
            "name": name,
            "title": title,
            "description": description,
            "defaults": defaults,
        })
    permission_registry.register(cls)
