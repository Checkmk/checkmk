#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The ``map`` pagetype.

Registering this makes maps first-class Checkmk pagetypes — ownership, the
publish/permission model and Activate Changes replication all come from the
pagetypes framework (like graph collections), without the Visuals
single_infos/context envelope. The Customize list and the map editor stay
maps-own (the SPA via ``maps.py``); maps deliberately register no generic
pagetype list/edit/show pages (``page_handlers`` is empty), so the ``maps.py``
route stays the SPA mount.
"""

from collections.abc import Mapping
from typing import override, Self

from cmk.gui import pagetypes
from cmk.gui.i18n import _
from cmk.gui.pages import PageHandler
from cmk.maps.gui.builtin_maps import builtin_map_configs
from cmk.maps.gui.type_defs import MapConfig, MapModel
from cmk.web.utils.icons import DynamicIcon, IconNames, StaticIcon


class MapPage(pagetypes.Overridable[MapConfig]):
    @override
    @classmethod
    def deserialize(cls, page_dict: Mapping[str, object]) -> Self:
        model = MapModel.model_validate(page_dict)
        return cls(
            MapConfig(
                name=model.name,
                title=model.title,
                description=model.description,
                owner=model.owner,
                public=model.public,
                hidden=model.hidden,
                map_type=model.map_type,
                connection_id=model.connection_id,
                object_count=model.object_count,
                map_spec=model.map_spec,
            )
        )

    @override
    def serialize(self) -> dict[str, object]:
        return MapModel(
            name=self.config.name,
            title=self.config.title,
            description=self.config.description,
            owner=self.config.owner,
            public=self.config.public,
            hidden=self.config.hidden,
            map_type=self.config.map_type,
            connection_id=self.config.connection_id,
            object_count=self.config.object_count,
            map_spec=dict(self.config.map_spec),
        ).model_dump()

    @override
    @classmethod
    def type_name(cls) -> str:
        return "map"

    @override
    @classmethod
    def type_icon(cls) -> StaticIcon | DynamicIcon:
        return StaticIcon(IconNames.topic_visualization)

    @override
    @classmethod
    def phrase(cls, phrase: pagetypes.PagetypePhrase) -> str:
        return {
            "title": _("Map"),
            "title_plural": _("Maps"),
            "add_to": _("Add to map"),
            "clone": _("Clone map"),
            "create": _("Create map"),
            "edit": _("Edit map"),
            "new": _("Add map"),
        }.get(phrase, pagetypes.Base.phrase(phrase))

    @override
    @classmethod
    def page_handlers(cls) -> dict[str, PageHandler]:
        # Maps own all their routes through the SPA (``maps.py``); the generic
        # pagetype list/edit/show pages would collide with that and are unused.
        return {}

    @override
    @classmethod
    def builtin_pages(cls) -> Mapping[str, MapConfig]:
        return builtin_map_configs()
