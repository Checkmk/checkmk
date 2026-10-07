#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import overload, override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import Row
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view_utils import CellSpec
from cmk.ruleset_matcher.tags import TagGroup
from cmk.web.utils.html import HTML
from cmk.web.utils.speaklater import LazyString

from .base import Cell, GroupValue, InternalPainter, PainterContext, RowFunction
from .host_tag_painters import HashableTagGroups, host_tag_config_based_painters
from .legacy import internal_painter_from_legacy, Painter


class PainterRegistry(Registry[InternalPainter]):
    @override
    def plugin_name(self, instance: InternalPainter) -> str:
        return instance.ident

    @overload
    def register(self, instance: InternalPainter) -> InternalPainter: ...

    @overload
    def register(self, instance: type[Painter]) -> type[Painter]: ...

    @override
    def register(
        self, instance: InternalPainter | type[Painter]
    ) -> InternalPainter | type[Painter]:
        if isinstance(instance, InternalPainter):
            return super().register(instance)
        super().register(internal_painter_from_legacy(instance))
        return instance


painter_registry = PainterRegistry()


def all_painters(tag_groups: Sequence[TagGroup]) -> dict[str, InternalPainter]:
    return dict(painter_registry.items()) | host_tag_config_based_painters(
        HashableTagGroups(tag_groups)
    )


type _PluginSpec = Mapping[str, object]
type _PaintFunction = Callable[[Row], object]
type _ExportFunction = Callable[[Row, Cell], object]


def _plugin_str(spec: _PluginSpec, key: str) -> str:
    if isinstance(value := spec[key], str):
        return value
    raise TypeError(f"{key!r} of a plug-in painter must be a str, not {value!r}")


def _plugin_optional_str(spec: _PluginSpec, key: str) -> str | None:
    return None if spec.get(key) is None else _plugin_str(spec, key)


def _plugin_title(spec: _PluginSpec, key: str) -> str | LazyString:
    if isinstance(value := spec[key], str | LazyString):
        return value
    raise TypeError(f"{key!r} of a plug-in painter must be a str or LazyString, not {value!r}")


def _plugin_strings(spec: _PluginSpec, key: str) -> Sequence[str]:
    value = spec.get(key, [])
    if isinstance(value, list | tuple) and all(isinstance(v, str) for v in value):
        return [str(v) for v in value]
    raise TypeError(f"{key!r} of a plug-in painter must be a list of str, not {value!r}")


def _plugin_bool(spec: _PluginSpec, key: str, default: bool) -> bool:
    if isinstance(value := spec.get(key, default), bool):
        return value
    raise TypeError(f"{key!r} of a plug-in painter must be a bool, not {value!r}")


def _plugin_printable(spec: _PluginSpec) -> bool | str:
    if isinstance(value := spec.get("printable", True), bool | str):
        return value
    raise TypeError(f"'printable' of a plug-in painter must be a bool or str, not {value!r}")


def _plugin_paint(spec: _PluginSpec) -> _PaintFunction:
    if callable(value := spec["paint"]):
        return value
    raise TypeError(f"'paint' of a plug-in painter must be callable, not {value!r}")


def _plugin_export(spec: _PluginSpec, key: str) -> _ExportFunction | None:
    if (value := spec.get(key)) is None or callable(value):
        return value
    raise TypeError(f"{key!r} of a plug-in painter must be callable, not {value!r}")


def _plugin_parameters(spec: _PluginSpec) -> ValueSpec[object] | None:
    if (value := spec.get("params")) is None or isinstance(value, ValueSpec):
        return value
    raise TypeError(f"'params' of a plug-in painter must be a ValueSpec, not {value!r}")


def _plugin_cell_spec(value: object) -> CellSpec:
    match value:
        case (str() | None as css_class, str() | HTML() as content):
            return css_class, content
        case (str() | None as css_class, LazyString() as content):
            return css_class, str(content)
        case (str() | None as css_class, Mapping() as content) if all(
            isinstance(key, str) for key in content
        ):
            return css_class, content
        case _:
            raise TypeError(
                f"A plug-in painter must paint a (CSS class, content) pair, not {value!r}"
            )


def _plugin_csv(value: object) -> str | HTML:
    return value if isinstance(value, str | HTML) else str(value)


def _render_plugin_painter(
    paint: _PaintFunction, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _plugin_cell_spec(paint(row))


def _export_painted_content(
    paint: _PaintFunction, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return _plugin_cell_spec(paint(row))[1]


def _export_plugin_painter(
    export: _ExportFunction, row: Row, cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return export(row, cell)


def _plugin_export_function(
    spec: _PluginSpec, key: str, paint: _PaintFunction
) -> RowFunction[object]:
    if (export := _plugin_export(spec, key)) is None:
        return partial(_export_painted_content, paint)
    return partial(_export_plugin_painter, export)


def _export_plugin_painter_for_csv(
    export: RowFunction[object], row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> str | HTML:
    return _plugin_csv(export(row, cell, user, context))


def _plugin_group_value(value: object) -> GroupValue:
    match value:
        case None | str():
            return value
        case tuple() if all(isinstance(entry, str) for entry in value):
            return tuple(str(entry) for entry in value)
        case tuple() if all(
            isinstance(entry, tuple)
            and len(entry) == 2
            and all(isinstance(part, str) for part in entry)
            for entry in value
        ):
            return tuple((str(entry[0]), str(entry[1])) for entry in value)
    raise TypeError(f"'groupby' of a plug-in painter must give a group value, not {value!r}")


def _group_by_static_value(
    value: GroupValue, _row: Row, _cell: Cell, _context: PainterContext
) -> GroupValue:
    return value


def _group_by_plugin_function(
    group_by: _PaintFunction, row: Row, _cell: Cell, _context: PainterContext
) -> GroupValue:
    return _plugin_group_value(group_by(row))


def _plugin_group_by(
    spec: _PluginSpec,
) -> Callable[[Row, Cell, PainterContext], GroupValue] | None:
    if "groupby" not in spec:
        return None
    if callable(value := spec["groupby"]):
        return partial(_group_by_plugin_function, value)
    return partial(_group_by_static_value, _plugin_group_value(value))


def _make_plugin_painter(ident: str, spec: _PluginSpec) -> InternalPainter:
    paint = _plugin_paint(spec)
    return InternalPainter(
        ident=ident,
        title=_plugin_title(spec, "title"),
        short_title=(None if spec.get("short") is None else _plugin_title(spec, "short")),
        tooltip_title=(
            None if spec.get("tooltip_title") is None else _plugin_title(spec, "tooltip_title")
        ),
        columns=_plugin_strings(spec, "columns"),
        sorter=_plugin_optional_str(spec, "sorter"),
        printable=_plugin_printable(spec),
        painter_options=_plugin_strings(spec, "options"),
        load_inv=_plugin_bool(spec, "load_inv", False),
        parameters=_plugin_parameters(spec),
        group_by=_plugin_group_by(spec),
        render=partial(_render_plugin_painter, paint),
        export_for_python=_plugin_export_function(spec, "export_for_python", paint),
        export_for_csv=partial(
            _export_plugin_painter_for_csv,
            _plugin_export_function(spec, "export_for_csv", paint),
        ),
        export_for_json=_plugin_export_function(spec, "export_for_json", paint),
    )


# Kept for pre 1.6 compatibility.
def register_painter(ident: str, spec: _PluginSpec) -> None:
    painter_registry.register(_make_plugin_painter(ident, spec))
