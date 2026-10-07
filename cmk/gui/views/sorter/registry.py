#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any, override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.config import Config
from cmk.gui.painter import EmptyCell, painter_registry
from cmk.gui.painter.host_tag_painters import HashableTagGroups
from cmk.gui.type_defs import ColumnName, PainterName, SorterFunction

from .base import Sorter
from .host_tag_sorters import host_tag_config_based_sorters


class SorterRegistry(Registry[Sorter]):
    @override
    def plugin_name(self, instance: Sorter) -> str:
        return instance.ident


sorter_registry = SorterRegistry()


def all_sorters(config: Config) -> dict[str, Sorter]:
    return dict(sorter_registry.items()) | host_tag_config_based_sorters(
        HashableTagGroups(config.tags.tag_groups)
    )


# Kept for pre 1.6 compatibility.
def register_sorter(ident: str, spec: dict[str, Any]) -> None:
    sorter_registry.register(
        Sorter(
            ident=ident,
            title=spec["title"],
            columns=spec["columns"],
            sort_function=lambda r1, r2, **_kwargs: spec["cmp"](r1, r2),
            load_inv=spec.get("load_inv", False),
        )
    )


def declare_simple_sorter(name: str, title: str, column: ColumnName, func: SorterFunction) -> None:
    sorter_registry.register(
        Sorter(
            ident=name,
            title=title,
            columns=[column],
            sort_function=lambda r1, r2, **_kwargs: func(column, r1, r2),
        )
    )


def declare_1to1_sorter(
    painter_name: PainterName, func: SorterFunction, col_num: int = 0, reverse: bool = False
) -> PainterName:
    painter = painter_registry[painter_name]
    cell = EmptyCell()

    sorter_registry.register(
        Sorter(
            ident=painter_name,
            title=painter.title(cell, cell.painter_context()),
            columns=painter.columns,
            sort_function=(
                (lambda r1, r2, **_kwargs: func(painter.columns[col_num], r2, r1))
                if reverse
                else lambda r1, r2, **_kwargs: func(painter.columns[col_num], r1, r2)
            ),
        )
    )

    return painter_name
