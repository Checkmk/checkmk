#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.ccc.plugin_registry import Registry

from cmk.gui.config import active_config, Config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme.current_theme import theme

from .base import Painter
from .helpers import RenderLink
from .host_tag_painters import HashableTagGroups, host_tag_config_based_painters


class PainterRegistry(Registry[type[Painter]]):
    def plugin_name(self, instance: type[Painter]) -> str:
        return instance(
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
        ).ident


painter_registry = PainterRegistry()


def all_painters(config: Config) -> dict[str, type[Painter]]:
    return dict(painter_registry.items()) | host_tag_config_based_painters(
        HashableTagGroups(config.tags.tag_groups)
    )


# Kept for pre 1.6 compatibility.
def register_painter(ident: str, spec: dict[str, Any]) -> None:
    paint_function = spec["paint"]
    cls = type(
        "LegacyPainter%s" % ident.title(),
        (Painter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": lambda s, cell: s._spec["title"],
            "short_title": lambda s, cell: s._spec.get("short", s.title),
            "tooltip_title": lambda s, cell: s._spec.get("tooltip_title", s.title),
            "columns": property(lambda s: s._spec["columns"]),
            "render": lambda self, row, cell, user: paint_function(row),
            "export_for_python": (
                lambda self, row, cell, user: (
                    spec["export_for_python"](row, cell)
                    if "export_for_python" in spec
                    else paint_function(row)[1]
                )
            ),
            "export_for_csv": (
                lambda self, row, cell, user: (
                    spec["export_for_csv"](row, cell)
                    if "export_for_csv" in spec
                    else paint_function(row)[1]
                )
            ),
            "export_for_json": (
                lambda self, row, cell, user: (
                    spec["export_for_json"](row, cell)
                    if "export_for_json" in spec
                    else paint_function(row)[1]
                )
            ),
            "group_by": lambda self, row, cell: self._spec.get("groupby"),
            "parameters": property(lambda s: s._spec.get("params")),
            "painter_options": property(lambda s: s._spec.get("options", [])),
            "printable": property(lambda s: s._spec.get("printable", True)),
            "sorter": property(lambda s: s._spec.get("sorter", None)),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
        },
    )
    painter_registry.register(cls)
