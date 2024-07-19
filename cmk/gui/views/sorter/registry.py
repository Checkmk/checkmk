#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Any

from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0.base import painter_registry
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import ColumnName, PainterName, SorterFunction
from cmk.gui.utils.theme import theme

from cmk.ccc.plugin_registry import Registry

from .base import Sorter


class SorterRegistry(Registry[type[Sorter]]):
    def plugin_name(self, instance: type[Sorter]) -> str:
        return instance(
            user=user,
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
        ).ident


sorter_registry = SorterRegistry()


# Kept for pre 1.6 compatibility.
def register_sorter(ident: str, spec: dict[str, Any]) -> None:
    cls = type(
        "LegacySorter%s" % str(ident).title(),
        (Sorter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._spec["title"]),
            "columns": property(lambda s: s._spec["columns"]),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
            "cmp": lambda self, r1, r2, p: spec["cmp"](r1, r2),
        },
    )
    sorter_registry.register(cls)


def declare_simple_sorter(name: str, title: str, column: ColumnName, func: SorterFunction) -> None:
    register_sorter(
        name,
        {"title": title, "columns": [column], "cmp": lambda r1, r2: func(column, r1, r2)},
    )


def declare_1to1_sorter(
    painter_name: PainterName, func: SorterFunction, col_num: int = 0, reverse: bool = False
) -> PainterName:
    painter = painter_registry[painter_name](
        user=user,
        config=active_config,
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
    )

    register_sorter(
        painter_name,
        {
            "title": painter.title,
            "columns": painter.columns,
            "cmp": (
                (lambda r1, r2: func(painter.columns[col_num], r2, r1))
                if reverse
                else lambda r1, r2: func(painter.columns[col_num], r1, r2)
            ),
        },
    )
    return painter_name
