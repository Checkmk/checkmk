#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Callable, Sequence
from functools import partial
from typing import Any, overload, override, TypeIs

from cmk.ccc.plugin_registry import Registry
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import Row
from cmk.gui.view_utils import CellSpec
from cmk.ruleset_matcher.tags import TagGroup

from .base import Cell, InternalPainter, PainterContext
from .host_tag_painters import HashableTagGroups, host_tag_config_based_painters
from .legacy import internal_painter_from_legacy, Painter


def _is_legacy_painter(
    instance: type[Painter] | Callable[[], InternalPainter],
) -> TypeIs[type[Painter]]:
    return isinstance(instance, type) and issubclass(instance, Painter)


class PainterRegistry(Registry[InternalPainter]):
    @override
    def plugin_name(self, instance: InternalPainter) -> str:
        return instance.ident

    @overload
    def register(self, instance: InternalPainter) -> InternalPainter: ...

    @overload
    def register(self, instance: type[Painter]) -> type[Painter]: ...

    @overload
    def register(
        self, instance: Callable[[], InternalPainter]
    ) -> Callable[[], InternalPainter]: ...

    @override
    def register(
        self, instance: InternalPainter | type[Painter] | Callable[[], InternalPainter]
    ) -> InternalPainter | type[Painter] | Callable[[], InternalPainter]:
        if isinstance(instance, InternalPainter):
            return super().register(instance)
        if _is_legacy_painter(instance):
            super().register(internal_painter_from_legacy(instance))
            return instance
        super().register(instance())
        return instance


painter_registry = PainterRegistry()


def all_painters(tag_groups: Sequence[TagGroup]) -> dict[str, InternalPainter]:
    return dict(painter_registry.items()) | host_tag_config_based_painters(
        HashableTagGroups(tag_groups)
    )


def _render_plugin_painter(
    spec: dict[str, Any], row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    cell_spec: CellSpec = spec["paint"](row)
    return cell_spec


def _export_plugin_painter(
    spec: dict[str, Any],
    key: str,
    row: Row,
    cell: Cell,
    _user: LoggedInUser,
    _context: PainterContext,
) -> Any:
    return spec[key](row, cell) if key in spec else spec["paint"](row)[1]


def _group_by_plugin_painter(
    spec: dict[str, Any], _row: Row, _cell: Cell, _context: PainterContext
) -> Any:
    return spec.get("groupby")


# Kept for pre 1.6 compatibility.
def register_painter(ident: str, spec: dict[str, Any]) -> None:
    painter_registry.register(
        InternalPainter(
            ident=ident,
            title=spec["title"],
            render=partial(_render_plugin_painter, spec),
            short_title=spec.get("short"),
            tooltip_title=spec.get("tooltip_title"),
            columns=spec["columns"],
            group_by=partial(_group_by_plugin_painter, spec),
            parameters=spec.get("params"),
            export_for_python=partial(_export_plugin_painter, spec, "export_for_python"),
            export_for_csv=partial(_export_plugin_painter, spec, "export_for_csv"),
            export_for_json=partial(_export_plugin_painter, spec, "export_for_json"),
            sorter=spec.get("sorter"),
            printable=spec.get("printable", True),
            painter_options=spec.get("options", []),
            load_inv=spec.get("load_inv", False),
        )
    )
