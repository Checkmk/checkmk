#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from pydantic import BaseModel

from cmk.ccc.plugin_registry import Registry

from cmk.gui import pagetypes
from cmk.gui.i18n import _
from cmk.gui.pages import page_registry, PageEndpoint
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.type_defs import Icon, PermissionName
from cmk.gui.valuespec import CascadingDropdown, CascadingDropdownChoice, Dictionary, ValueSpec

from ._base import CustomizableSidebarSnapin, SidebarSnapin
from ._permission_section import PERMISSION_SECTION_SIDEBAR_SNAPINS

# TODO: Actually this is cmk.gui.sidebar.CustomSnapins, but we run into a hell
# of cycles and untyped dependencies. So for now this is just a reminder.


# TODO: We should really register instances instead of classes here... :-/ Using
# classes obfuscates the code and makes typing a nightmare.
class SnapinRegistry(Registry[type[SidebarSnapin]]):
    """The management object for all available plugins."""

    def plugin_name(self, instance: type[SidebarSnapin]) -> str:
        return instance.type_name()

    def registration_hook(self, instance: type[SidebarSnapin]) -> None:
        permission_registry.register(
            Permission(
                section=PERMISSION_SECTION_SIDEBAR_SNAPINS,
                name=self.plugin_name(instance),
                title=instance.title(),
                description=instance.description(),
                defaults=instance.allowed_roles(),
            )
        )

        for path, page_func in instance().page_handlers().items():
            page_registry.register(PageEndpoint(path, page_func))

    def get_customizable_snapin_types(self) -> list[tuple[str, type[CustomizableSidebarSnapin]]]:
        return [
            (snapin_type_id, snapin_type)
            for snapin_type_id, snapin_type in self.items()
            if issubclass(snapin_type, CustomizableSidebarSnapin)
        ]


snapin_registry = SnapinRegistry()


# .
#   .--Custom-Snapins------------------------------------------------------.
#   |       ____          _     ____                    _                  |
#   |      / ___|   _ ___| |_  / ___| _ __   __ _ _ __ (_)_ __  ___        |
#   |     | |  | | | / __| __| \___ \| '_ \ / _` | '_ \| | '_ \/ __|       |
#   |     | |__| |_| \__ \ |_ _ ___) | | | | (_| | |_) | | | | \__ \       |
#   |      \____\__,_|___/\__(_)____/|_| |_|\__,_| .__/|_|_| |_|___/       |
#   |                                            |_|                       |
#   '----------------------------------------------------------------------'


class CustomSnapinParamsRowModel(BaseModel):
    title: str
    query: tuple[Literal["hosts", "services", "events"], dict]


class CustomSnapinParamsModel(BaseModel):
    rows: list[CustomSnapinParamsRowModel]
    show_failed_notifications: bool = True
    show_sites_not_connected: bool = True
    show_stale: bool = True


class CustomSnapinsModel(pagetypes.OverridableModel):
    custom_snapin: tuple[str, CustomSnapinParamsModel]


@dataclass
class CustomSnapinParamsRowConfig:
    title: str
    query: tuple[Literal["hosts", "services", "events"], dict]


@dataclass
class CustomSnapinParamsConfig:
    rows: list[CustomSnapinParamsRowConfig]
    show_failed_notifications: bool
    show_sites_not_connected: bool
    show_stale: bool


@dataclass(kw_only=True)
class CustomSnapinsConfig(pagetypes.OverridableConfig):
    custom_snapin: tuple[str, CustomSnapinParamsConfig]


class CustomSnapins(pagetypes.Overridable[CustomSnapinsConfig]):
    @classmethod
    def deserialize(cls, page_dict: Mapping[str, object]) -> Self:
        _model = CustomSnapinsModel.model_validate(page_dict)
        return cls(
            CustomSnapinsConfig(
                name=_model.name,
                title=_model.title,
                description=_model.description,
                owner=_model.owner,
                public=_model.public,
                hidden=_model.hidden,
                custom_snapin=(
                    _model.custom_snapin[0],
                    CustomSnapinParamsConfig(
                        rows=[
                            CustomSnapinParamsRowConfig(title=r.title, query=r.query)
                            for r in _model.custom_snapin[1].rows
                        ],
                        show_failed_notifications=_model.custom_snapin[1].show_failed_notifications,
                        show_sites_not_connected=_model.custom_snapin[1].show_sites_not_connected,
                        show_stale=_model.custom_snapin[1].show_stale,
                    ),
                ),
            )
        )

    def serialize(self) -> dict[str, object]:
        return CustomSnapinsModel(
            name=self.config.name,
            title=self.config.title,
            description=self.config.description,
            owner=self.config.owner,
            public=self.config.public,
            hidden=self.config.hidden,
            custom_snapin=(
                self.config.custom_snapin[0],
                CustomSnapinParamsModel(
                    rows=[
                        CustomSnapinParamsRowModel(title=r.title, query=r.query)
                        for r in self.config.custom_snapin[1].rows
                    ],
                    show_failed_notifications=self.config.custom_snapin[
                        1
                    ].show_failed_notifications,
                    show_sites_not_connected=self.config.custom_snapin[1].show_sites_not_connected,
                    show_stale=self.config.custom_snapin[1].show_stale,
                ),
            ),
        ).model_dump()

    @classmethod
    def type_name(cls) -> str:
        return "custom_snapin"

    @classmethod
    def type_icon(cls) -> Icon:
        return "custom_snapin"

    @classmethod
    def type_is_show_more(cls) -> bool:
        return True

    @classmethod
    def phrase(cls, phrase: pagetypes.PagetypePhrase) -> str:
        return {
            "title": _("Custom sidebar element"),
            "title_plural": _("Custom sidebar elements"),
            # "add_to"         : _("Add to custom element list"),
            "clone": _("Clone element"),
            "create": _("Create element"),
            "edit": _("Edit element"),
            "new": _("Add element"),
        }.get(phrase, pagetypes.Base.phrase(phrase))

    @classmethod
    def parameters(
        cls, mode: pagetypes.PageMode
    ) -> list[tuple[str, list[tuple[float, str, ValueSpec]]]]:
        parameters = super().parameters(mode)

        parameters += [
            (
                cls.phrase("title"),
                # sort-index, key, valuespec
                [
                    (
                        2.5,
                        "custom_snapin",
                        CascadingDropdown(
                            title=_("Element type"),
                            choices=cls._customizable_snapin_type_choices,
                        ),
                    )
                ],
            )
        ]

        return parameters

    @classmethod
    def _customizable_snapin_type_choices(cls) -> Sequence[CascadingDropdownChoice]:
        choices = []
        for snapin_type_id, snapin_type in sorted(snapin_registry.get_customizable_snapin_types()):
            choices.append(
                (
                    snapin_type_id,
                    snapin_type.title(),
                    Dictionary(
                        title=_("Parameters"),
                        elements=snapin_type.vs_parameters(),
                        optional_keys=[],
                    ),
                )
            )
        return choices

    @classmethod
    def reserved_unique_ids(cls) -> list[str]:
        return list(snapin_registry)


def custom_snapin_classes(
    list_custom_snapins: list[CustomSnapins],
) -> dict[str, type[SidebarSnapin]]:
    snapins: dict[str, type[SidebarSnapin]] = {}
    for custom_snapin in list_custom_snapins:
        base_snapin_type_id = custom_snapin.config.custom_snapin[0]

        try:
            base_snapin_type = snapin_registry[base_snapin_type_id]
        except KeyError:
            continue

        # TODO: This is just our assumption, can we enforce this via
        # typing? Probably not in the current state of affairs where things
        # which should be instances are classes... :-/
        if not issubclass(base_snapin_type, SidebarSnapin):
            raise ValueError("invalid snap-in type %r" % base_snapin_type)

        if not issubclass(base_snapin_type, CustomizableSidebarSnapin):
            continue

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

        snapins[CustomSnapin.type_name()] = CustomSnapin

    return snapins


def all_snapins() -> dict[str, type[SidebarSnapin]]:
    return dict(snapin_registry.items()) | custom_snapin_classes(
        CustomSnapins.load().instances_sorted()
    )
