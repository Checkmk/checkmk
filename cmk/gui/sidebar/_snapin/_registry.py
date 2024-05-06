#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.utils.plugin_registry import Registry

from cmk.gui.pages import page_registry
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.type_defs import PermissionName

from ._base import CustomizableSidebarSnapin, SidebarSnapin
from ._permission_section import PermissionSectionSidebarSnapins

# TODO: Actually this is cmk.gui.sidebar.CustomSnapins, but we run into a hell
# of cycles and untyped dependencies. So for now this is just a reminder.
CustomSnapins = Any


# TODO: We should really register instances instead of classes here... :-/ Using
# classes obfuscates the code and makes typing a nightmare.
class SnapinRegistry(Registry[type[SidebarSnapin]]):
    """The management object for all available plugins."""

    def plugin_name(self, instance: type[SidebarSnapin]) -> str:
        return instance.type_name()

    def registration_hook(self, instance: type[SidebarSnapin]) -> None:
        # Custom snap-ins have their own permissions "custom_snapin.*"
        if not instance.is_custom_snapin():
            permission_registry.register(
                Permission(
                    section=PermissionSectionSidebarSnapins,
                    name=self.plugin_name(instance),
                    title=instance.title(),
                    description=instance.description(),
                    defaults=instance.allowed_roles(),
                )
            )

        for path, page_func in instance().page_handlers().items():
            page_registry.register_page_handler(path, page_func)

    def get_customizable_snapin_types(self) -> list[tuple[str, type[CustomizableSidebarSnapin]]]:
        return [
            (snapin_type_id, snapin_type)
            for snapin_type_id, snapin_type in self.items()
            if (
                issubclass(snapin_type, CustomizableSidebarSnapin)
                and not snapin_type.is_custom_snapin()
            )
        ]

    def register_custom_snapins(self, custom_snapins: list[CustomSnapins]) -> None:
        """Extends the snap-in registry with the ones configured in the site (for the current user)"""
        self._clear_custom_snapins()
        self._add_custom_snapins(custom_snapins)

    def _clear_custom_snapins(self) -> None:
        for snapin_type_id, snapin_type in list(self.items()):
            if snapin_type.is_custom_snapin():
                self.unregister(snapin_type_id)

    def _add_custom_snapins(self, custom_snapins: list[CustomSnapins]) -> None:
        for custom_snapin in custom_snapins:
            base_snapin_type_id = custom_snapin.config.custom_snapin[0]

            try:
                base_snapin_type = self[base_snapin_type_id]
            except KeyError:
                continue

            # TODO: This is just our assumption, can we enforce this via
            # typing? Probably not in the current state of affairs where things
            # which should be instances are classes... :-/
            if not issubclass(base_snapin_type, SidebarSnapin):
                raise ValueError("invalid snapin type %r" % base_snapin_type)

            if not issubclass(base_snapin_type, CustomizableSidebarSnapin):
                continue

            # TODO: The stuff below is completely untypeable... :-P * * *
            @self.register
            class CustomSnapin(base_snapin_type):  # type: ignore[valid-type,misc]
                _custom_snapin = custom_snapin

                @classmethod
                def is_custom_snapin(cls) -> bool:
                    return True

                @classmethod
                def type_name(cls):
                    return cls._custom_snapin.name()

                @classmethod
                def title(cls):
                    return cls._custom_snapin.title()

                @classmethod
                def description(cls):
                    return cls._custom_snapin.description()

                @classmethod
                def parameters(cls):
                    return cls._custom_snapin.config.custom_snapin[1]

                @classmethod
                def permission_name(cls) -> PermissionName:
                    return "custom_snapin.%s" % cls.type_name()

                @classmethod
                def may_see(cls) -> bool:
                    return cls._custom_snapin.is_permitted()

            _it_is_really_used = CustomSnapin  # noqa: F841


snapin_registry = SnapinRegistry()
