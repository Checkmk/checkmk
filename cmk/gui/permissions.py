#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import override

import cmk.ccc.plugin_registry
from cmk.gui.type_defs import RoleName
from cmk.web.utils.permission_verification import PermissionName
from cmk.web.utils.speaklater import LazyString, LazyText


@dataclass(frozen=True, kw_only=True)
class PermissionSection:
    """The identity of a permission section.
    One word, may contain alpha numeric characters"""

    name: str
    """Display name representing the section"""
    title: str
    """Number to sort the sections with"""
    sort_index: int = 50
    """Whether or not to sort the permissions by title in this section"""
    do_sort: bool = False


class PermissionSectionRegistry(cmk.ccc.plugin_registry.Registry[PermissionSection]):
    @override
    def plugin_name(self, instance: PermissionSection) -> str:
        return instance.name

    def get_sorted_sections(self) -> list[PermissionSection]:
        return sorted(self.values(), key=lambda s: (s.sort_index, s.title))


permission_section_registry = PermissionSectionRegistry()


class Permission:
    _sort_index = 0

    def __init__(
        self,
        section: PermissionSection,
        name: str,
        title: str | LazyString | LazyText,
        description: str | LazyString | LazyText,
        defaults: Sequence[RoleName],
    ) -> None:
        self._section = section
        self._name = name
        self._title = title
        self._description = description
        self._defaults = defaults
        self._sort_index = 0

    @property
    def section(self) -> PermissionSection:
        return self._section

    @property
    def permission_name(self) -> str:
        """The identity of a permission (without it's section identity).
        One word, may contain alpha numeric characters"""
        return self._name

    @property
    def title(self) -> str:
        """Display name representing the permission"""
        return str(self._title)

    @property
    def description(self) -> str:
        """Text to explain the purpose of this permission"""
        return str(self._description)

    @property
    def defaults(self) -> Sequence[str]:
        """List of role IDs that have this permission by default"""
        return self._defaults

    @property
    def name(self) -> str:
        """The full identity of a permission (including the section identity)."""
        return f"{self.section.name}.{self.permission_name}"

    @property
    def sort_index(self) -> int:
        """Number to sort the permission with"""
        return self._sort_index

    @sort_index.setter
    def sort_index(self, value: int) -> None:
        self._sort_index = value


class PermissionRegistry(cmk.ccc.plugin_registry.Registry[Permission]):
    def __init__(self) -> None:
        super().__init__()
        # TODO: Better make the sorting explicit in the future
        # used as auto incrementing counter to numerate the permissions in
        # the order they have been added.
        self._index_counter = 0

    @override
    def plugin_name(self, instance: Permission) -> str:
        return instance.name

    @override
    def registration_hook(self, instance: Permission) -> None:
        instance._sort_index = self._index_counter  # noqa: SLF001
        self._index_counter += 1

    def get_sorted_permissions(self, section: PermissionSection) -> list[Permission]:
        """Returns the sorted permissions of a section respecting the sorting config of the section"""
        permissions = [p for p in self.values() if p.section.name == section.name]

        if section.do_sort:
            return sorted(permissions, key=lambda p: (p.title, p.sort_index))
        return sorted(permissions, key=lambda p: p.sort_index)

    @override
    def register(self, instance: Permission) -> Permission:
        # A permission registered again is sorted by its last registration
        if (name := self.plugin_name(instance)) in self:
            self.unregister(name)
        return super().register(instance)


permission_registry = PermissionRegistry()


def declare_permission_section(
    name: str, title: str, prio: int = 50, do_sort: bool = False
) -> None:
    permission_section_registry.register(
        PermissionSection(
            name=name,
            title=title,
            sort_index=prio,
            do_sort=do_sort,
        )
    )


def declare_permission(
    name: PermissionName,
    title: str | LazyString | LazyText,
    description: str | LazyString | LazyText,
    defaults: Sequence[RoleName],
) -> None:
    section_name, permission_name = name.split(".", 1)

    permission_registry.register(
        Permission(
            section=permission_section_registry[section_name],
            name=permission_name,
            title=title,
            description=description,
            defaults=defaults,
        )
    )


_permission_declaration_functions: list[Callable[[], None]] = []


# Some module have a non-fixed list of permissions. For example for
# each user defined view there is also a permission. This list is
# not known at the time of the loading of the module - though. For
# that purpose module can register functions. These functions should
# just call declare_permission(). They are being called in the correct
# situations.
def declare_dynamic_permissions(func: Callable[[], None]) -> None:
    _permission_declaration_functions.append(func)


# This function needs to be called by all code that needs access
# to possible dynamic permissions
def load_dynamic_permissions() -> None:
    for func in _permission_declaration_functions:
        func()


type DynamicPermissionsProvider = Callable[[], Iterable[Permission]]


class DynamicPermissionRegistry(Mapping[str, Sequence[DynamicPermissionsProvider]]):
    """The providers of the permissions which are not known at import time, by section name

    For example for each user defined view there is also a permission. A
    provider computes the permissions of its section on demand. It must not
    change registries or other global state. Updating a cache it reads from
    is fine."""

    def __init__(self) -> None:
        self._providers: dict[str, list[DynamicPermissionsProvider]] = {}

    def register(self, section_name: str, provider: DynamicPermissionsProvider) -> None:
        providers = self._providers.setdefault(section_name, [])
        if provider not in providers:
            providers.append(provider)

    @override
    def __getitem__(self, key: str) -> Sequence[DynamicPermissionsProvider]:
        return self._providers[key]

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._providers)

    @override
    def __len__(self) -> int:
        return len(self._providers)


dynamic_permission_registry = DynamicPermissionRegistry()


class AllPermissions(Mapping[str, Permission]):
    """The static permissions plus the dynamic ones

    The dynamic permissions of a section are computed on the first access to a
    permission of the section which is not a static one. Iterating computes the
    permissions of all sections."""

    def __init__(
        self,
        static: Mapping[str, Permission],
        providers: Mapping[str, Sequence[DynamicPermissionsProvider]],
    ) -> None:
        self._static = static
        self._providers = providers
        self._dynamic: dict[str, dict[str, Permission]] = {}

    def _dynamic_of_section(self, section_name: str) -> Mapping[str, Permission]:
        if (permissions := self._dynamic.get(section_name)) is None:
            permissions = self._dynamic[section_name] = {}
            for provider in self._providers.get(section_name, []):
                for p in provider():
                    # The first declaration of a permission wins
                    if p.name not in self._static and p.name not in permissions:
                        permissions[p.name] = p
        return permissions

    @override
    def __getitem__(self, key: str) -> Permission:
        if (permission := self._static.get(key)) is not None:
            return permission
        return self._dynamic_of_section(key.split(".", 1)[0])[key]

    @override
    def __iter__(self) -> Iterator[str]:
        yield from self._static
        for section_name in self._providers:
            yield from self._dynamic_of_section(section_name)

    @override
    def __len__(self) -> int:
        return len(self._static) + sum(
            len(self._dynamic_of_section(section_name)) for section_name in self._providers
        )


def all_permissions() -> AllPermissions:
    """The permissions of the registered static permissions and dynamic permission providers"""
    return AllPermissions(permission_registry, dynamic_permission_registry)


def get_sorted_permissions(
    permissions: Mapping[str, Permission], section: PermissionSection
) -> list[Permission]:
    """Returns the sorted permissions of a section respecting the sorting config of the section

    Without sorting by title, the permissions keep the order they have been declared in."""
    section_permissions = [p for p in permissions.values() if p.section.name == section.name]
    if section.do_sort:
        return sorted(section_permissions, key=lambda p: p.title)
    return section_permissions
