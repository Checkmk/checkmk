#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Callable, TypedDict

from livestatus import SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    ImmutableAttributes,
    ImmutableDeltaTree,
    ImmutableTree,
    SDKey,
    SDPath,
    SDRawDeltaTree,
    SDRawTree,
    SDValue,
)

import cmk.gui.sites as sites
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.painter.v0.base import Cell, Painter
from cmk.gui.painter_options import paint_age, PainterOption, PainterOptions
from cmk.gui.type_defs import ColumnName, PainterParameters, Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.valuespec import Checkbox, Dictionary, FixedValue, ValueSpec
from cmk.gui.view_utils import CellSpec, CSVExportError

from ._display_hints import AttributeDisplayHint, ColumnDisplayHint, NodeDisplayHint
from ._tree_renderer import compute_cell_spec, SDItem, TreeRenderer


@request_memoize()
def _get_sites_with_same_named_hosts_cache() -> Mapping[HostName, Sequence[SiteId]]:
    cache: dict[HostName, list[SiteId]] = {}
    query_str = "GET hosts\nColumns: host_name\n"
    with sites.prepend_site():
        for row in sites.live().query(query_str):
            cache.setdefault(HostName(row[1]), []).append(SiteId(row[0]))
    return cache


class MultipleInventoryTreesError(Exception):
    pass


def _validate_inventory_tree_uniqueness(row: Row) -> None:
    raw_hostname = row.get("host_name")
    assert isinstance(raw_hostname, str)

    if (
        len(
            sites_with_same_named_hosts := _get_sites_with_same_named_hosts_cache().get(
                HostName(raw_hostname), []
            )
        )
        > 1
    ):
        html.show_error(
            _("Cannot display inventory tree of host '%s': Found this host on multiple sites: %s")
            % (raw_hostname, ", ".join(sites_with_same_named_hosts))
        )
        raise MultipleInventoryTreesError()


class PainterOptionShowInternalTreePaths(PainterOption):
    @property
    def ident(self) -> str:
        return "show_internal_tree_paths"

    @property
    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Show internal tree paths"),
            default_value=False,
        )


class PainterInventoryTree(Painter):
    @property
    def ident(self) -> str:
        return "inventory_tree"

    def title(self, cell):
        return _("Inventory Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_inventory", "host_structured_status"]

    @property
    def painter_options(self):
        return ["show_internal_tree_paths"]

    @property
    def load_inv(self):
        return True

    def _compute_data(self, row: Row, cell: Cell) -> ImmutableTree:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return ImmutableTree()

        return row.get("host_inventory", ImmutableTree())

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not (tree := self._compute_data(row, cell)):
            return "", ""

        tree_renderer = TreeRenderer(
            row["site"],
            row["host_name"],
            show_internal_tree_paths=self._painter_options.get("show_internal_tree_paths"),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, self.request)
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> SDRawTree:
        return self._compute_data(row, cell).serialize()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> SDRawTree:
        return self._compute_data(row, cell).serialize()


class PainterInvhistTime(Painter):
    @property
    def ident(self) -> str:
        return "invhist_time"

    def title(self, cell: Cell) -> str:
        return _("Inventory Date/Time")

    def short_title(self, cell: Cell) -> str:
        return _("Date/Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["invhist_time"],
            True,
            60 * 10,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterInvhistDelta(Painter):
    @property
    def ident(self) -> str:
        return "invhist_delta"

    def title(self, cell: Cell) -> str:
        return _("Inventory changes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_delta", "invhist_time"]

    def _compute_data(self, row: Row, cell: Cell) -> ImmutableDeltaTree:
        try:
            _validate_inventory_tree_uniqueness(row)
        except MultipleInventoryTreesError:
            return ImmutableDeltaTree()

        return row.get("invhist_delta", ImmutableDeltaTree())

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not (tree := self._compute_data(row, cell)):
            return "", ""

        tree_renderer = TreeRenderer(
            row["site"],
            row["host_name"],
            tree_id=str(row["invhist_time"]),
        )

        with output_funnel.plugged():
            tree_renderer.show(tree, self.request)
            code = HTML(output_funnel.drain())

        return "invtree", code

    def export_for_python(self, row: Row, cell: Cell) -> SDRawDeltaTree:
        return self._compute_data(row, cell).serialize()

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> SDRawDeltaTree:
        return self._compute_data(row, cell).serialize()


def _paint_invhist_count(row: Row, what: str) -> CellSpec:
    number = row["invhist_" + what]
    if number:
        return "narrow number", str(number)
    return "narrow number unused", "0"


class PainterInvhistRemoved(Painter):
    @property
    def ident(self) -> str:
        return "invhist_removed"

    def title(self, cell: Cell) -> str:
        return _("Removed entries")

    def short_title(self, cell: Cell) -> str:
        return _("Removed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_removed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "removed")


class PainterInvhistNew(Painter):
    @property
    def ident(self) -> str:
        return "invhist_new"

    def title(self, cell: Cell) -> str:
        return _("New entries")

    def short_title(self, cell: Cell) -> str:
        return _("New")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_new"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "new")


class PainterInvhistChanged(Painter):
    @property
    def ident(self) -> str:
        return "invhist_changed"

    def title(self, cell: Cell) -> str:
        return _("Changed entries")

    def short_title(self, cell: Cell) -> str:
        return _("Changed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["invhist_changed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_invhist_count(row, "changed")


class AttributePainterFromHint(TypedDict):
    title: str
    short: str
    tooltip_title: str
    columns: Sequence[str]
    options: Sequence[str]
    params: Dictionary
    printable: bool
    load_inv: bool
    sorter: str
    paint: Callable[[Row], CellSpec]
    export_for_python: Callable[[Row, Cell], SDValue]
    export_for_csv: Callable[[Row, Cell], str | HTML]
    export_for_json: Callable[[Row, Cell], SDValue]


def _get_attributes(row: Row, path: SDPath) -> ImmutableAttributes | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None
    return row.get("host_inventory", ImmutableTree()).get_tree(path).attributes


def _compute_attribute_painter_data(row: Row, path: SDPath, key: SDKey) -> SDValue:
    if (attributes := _get_attributes(row, path)) is None:
        return None
    return attributes.pairs.get(key)


def _paint_host_inventory_attribute(
    row: Row, path: SDPath, key: SDKey, hint: AttributeDisplayHint
) -> CellSpec:
    if (attributes := _get_attributes(row, path)) is None:
        return "", ""
    return compute_cell_spec(
        SDItem(
            key,
            attributes.pairs.get(key),
            attributes.retentions.get(key),
        ),
        hint,
    )


def attribute_painter_from_hint(
    path: SDPath, key: SDKey, ident: str, hint: AttributeDisplayHint
) -> AttributePainterFromHint:
    return AttributePainterFromHint(
        title=hint.long_inventory_title,
        # The short titles (used in column headers) may overlap for different painters, e.g.:
        # - BIOS > Version
        # - Firmware > Version
        # We want to keep column titles short, yet, to make up for overlapping we show the
        # long_title in the column title tooltips
        short=hint.short_title,
        tooltip_title=hint.long_title,
        columns=["host_inventory", "host_structured_status"],
        options=["show_internal_tree_paths"],
        params=Dictionary(
            title=_("Report options"),
            elements=[
                (
                    "use_short",
                    Checkbox(
                        title=_("Use short title in reports header"),
                        default_value=False,
                    ),
                ),
            ],
            required_keys=["use_short"],
        ),
        printable=True,
        load_inv=True,
        sorter=ident,
        paint=lambda row: _paint_host_inventory_attribute(row, path, key, hint),
        export_for_python=lambda row, cell: _compute_attribute_painter_data(row, path, key),
        export_for_csv=lambda row, cell: (
            "" if (data := _compute_attribute_painter_data(row, path, key)) is None else str(data)
        ),
        export_for_json=lambda row, cell: _compute_attribute_painter_data(row, path, key),
    )


class ColumnPainterFromHint(TypedDict):
    title: str
    short: str
    tooltip_title: str
    columns: Sequence[str]
    params: FixedValue
    sorter: str
    paint: Callable[[Row], CellSpec]
    export_for_python: Callable[[Row, Cell], SDValue]
    export_for_csv: Callable[[Row, Cell], str | HTML]
    export_for_json: Callable[[Row, Cell], SDValue]


def _paint_host_inventory_column(row: Row, ident: str, hint: ColumnDisplayHint) -> CellSpec:
    if ident not in row:
        return "", ""
    return compute_cell_spec(
        SDItem(
            SDKey(ident),
            row[ident],
            row.get("_".join([ident, "retention_interval"])),
        ),
        hint,
    )


def column_painter_from_hint(ident: str, hint: ColumnDisplayHint) -> ColumnPainterFromHint:
    return ColumnPainterFromHint(
        title=hint.long_inventory_title,
        # The short titles (used in column headers) may overlap for different painters, e.g.:
        # - BIOS > Version
        # - Firmware > Version
        # We want to keep column titles short, yet, to make up for overlapping we show the
        # long_title in the column title tooltips
        short=hint.short_title,
        tooltip_title=hint.long_title,
        columns=[ident],
        # See views/painter/v0/base.py::Cell.painter_parameters
        # We have to add a dummy value here such that the painter_parameters are not None and
        # the "real" parameters, ie. _painter_params, are used.
        params=FixedValue(PainterParameters(), totext=""),
        sorter=ident,
        paint=lambda row: _paint_host_inventory_column(row, ident, hint),
        export_for_python=lambda row, cell: row.get(ident),
        export_for_csv=lambda row, cell: "" if (data := row.get(ident)) is None else str(data),
        export_for_json=lambda row, cell: row.get(ident),
    )


class NodePainterFromHint(TypedDict):
    title: str
    short: str
    columns: Sequence[str]
    options: Sequence[str]
    params: Dictionary
    printable: bool
    load_inv: bool
    sorter: str
    paint: Callable[[Row], CellSpec]
    export_for_python: Callable[[Row, Cell], SDRawTree]
    export_for_csv: Callable[[Row, Cell], str | HTML]
    export_for_json: Callable[[Row, Cell], SDRawTree]


def _compute_node_painter_data(row: Row, path: SDPath) -> ImmutableTree:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return ImmutableTree()

    return row.get("host_inventory", ImmutableTree()).get_tree(path)


def _paint_host_inventory_tree(row: Row, path: SDPath, painter_options: PainterOptions) -> CellSpec:
    if not (tree := _compute_node_painter_data(row, path)):
        return "", ""

    tree_renderer = TreeRenderer(
        row["site"],
        row["host_name"],
        show_internal_tree_paths=painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(tree, request)
        code = HTML(output_funnel.drain())

    return "invtree", code


def _export_node_for_csv() -> str | HTML:
    raise CSVExportError()


def node_painter_from_hint(
    hint: NodeDisplayHint, painter_options: PainterOptions
) -> NodePainterFromHint:
    return NodePainterFromHint(
        title=hint.long_inventory_title,
        short=hint.short_title,
        columns=["host_inventory", "host_structured_status"],
        options=["show_internal_tree_paths"],
        params=Dictionary(
            title=_("Report options"),
            elements=[
                (
                    "use_short",
                    Checkbox(
                        title=_("Use short title in reports header"),
                        default_value=False,
                    ),
                ),
            ],
            required_keys=["use_short"],
        ),
        # Only attributes can be shown in reports. There is currently no way to render trees.
        # The HTML code would simply be stripped by the default rendering mechanism which does
        # not look good for the HW/SW inventory tree
        printable=False,
        load_inv=True,
        sorter=hint.ident,
        paint=lambda row: _paint_host_inventory_tree(row, hint.path, painter_options),
        export_for_python=lambda row, cell: (
            _compute_node_painter_data(row, hint.path).serialize()
        ),
        export_for_csv=lambda row, cell: _export_node_for_csv(),
        export_for_json=lambda row, cell: _compute_node_painter_data(row, hint.path).serialize(),
    )
