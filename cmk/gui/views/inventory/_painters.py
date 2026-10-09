#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, Sequence
from functools import partial

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter import Cell, InternalPainter, PainterContext
from cmk.gui.painter_options import paint_age, PainterOption
from cmk.gui.theme import Theme
from cmk.gui.type_defs import PainterParameters, Row
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.valuespec import Checkbox, Dictionary, FixedValue
from cmk.gui.view_utils import CellSpec, CSVExportError
from cmk.inventory.delta import ImmutableDeltaTree
from cmk.inventory.serialization import (
    SDRawDeltaTree,
    SDRawTree,
    serialize_delta_tree,
    serialize_tree,
)
from cmk.inventory.trees import ImmutableAttributes, ImmutableTree, SDKey, SDPath, SDValue
from cmk.web.utils.html import HTML

from ._display_hints import (
    AttributeDisplayHint,
    ColumnDisplayHintOfView,
    inv_display_hints,
    NodeDisplayHint,
)
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
        raise MultipleInventoryTreesError(
            _(
                "Cannot display inventory tree of host '%(host_name)s': found this host on multiple sites: %(sites)s"
            )
            % {"host_name": raw_hostname, "sites": ", ".join(sites_with_same_named_hosts)}
        )


def _multiple_trees_cell(row: Row) -> CellSpec | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError as error:
        return "", HTMLWriter.render_div(str(error), class_="error")
    return None


def _get_inventory_tree(row: Row) -> ImmutableTree:
    return tree if isinstance(tree := row.get("host_inventory"), ImmutableTree) else ImmutableTree()


def _get_delta_tree(row: Row) -> ImmutableDeltaTree:
    return (
        tree
        if isinstance(tree := row.get("invhist_delta"), ImmutableDeltaTree)
        else ImmutableDeltaTree()
    )


class PainterOptionShowInternalTreePaths(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="show_internal_tree_paths",
            valuespec=Checkbox(
                title=_("Show internal tree paths"),
                default_value=False,
            ),
        )


def _compute_data_inventory_tree(
    row: Row, _user: LoggedInUser, _context: PainterContext
) -> ImmutableTree:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return ImmutableTree()

    return _get_inventory_tree(row)


def _render_inventory_tree(
    row: Row, _cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if (error_cell := _multiple_trees_cell(row)) is not None:
        return error_cell
    if not (tree := _compute_data_inventory_tree(row, acting_user, context)):
        return "", ""

    tree_renderer = TreeRenderer(
        site_id=row["site"],
        host_name=row["host_name"],
        hints=inv_display_hints,
        theme=context.theme,
        request=context.request,
        show_internal_tree_paths=context.painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(time.time(), tree)
        code = HTML.without_escaping(output_funnel.drain())

    return "invtree", code


def _export_for_python_inventory_tree(
    row: Row, _cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> SDRawTree:
    return serialize_tree(_compute_data_inventory_tree(row, acting_user, context))


def _export_for_csv_inventory_tree(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def _export_for_json_inventory_tree(
    row: Row, _cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> SDRawTree:
    return serialize_tree(_compute_data_inventory_tree(row, acting_user, context))


def make_inventory_tree_painter() -> InternalPainter:
    return InternalPainter(
        ident="inventory_tree",
        title=_l("Inventory tree"),
        columns=["host_inventory", "host_structured_status"],
        painter_options=["show_internal_tree_paths"],
        load_inv=True,
        render=_render_inventory_tree,
        compute_data=_compute_data_inventory_tree,
        export_for_python=_export_for_python_inventory_tree,
        export_for_csv=_export_for_csv_inventory_tree,
        export_for_json=_export_for_json_inventory_tree,
    )


def _render_invhist_time(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["invhist_time"],
        True,
        60 * 10,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_invhist_time_painter() -> InternalPainter:
    return InternalPainter(
        ident="invhist_time",
        title=_l("Inventory date/time"),
        short_title=_l("Date/time"),
        columns=["invhist_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_invhist_time,
    )


def _compute_data_invhist_delta(
    row: Row, _user: LoggedInUser, _context: PainterContext
) -> ImmutableDeltaTree:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return ImmutableDeltaTree()

    return _get_delta_tree(row)


def _render_invhist_delta(
    row: Row, _cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if (error_cell := _multiple_trees_cell(row)) is not None:
        return error_cell
    if not (tree := _compute_data_invhist_delta(row, acting_user, context)):
        return "", ""

    tree_renderer = TreeRenderer(
        site_id=row["site"],
        host_name=row["host_name"],
        hints=inv_display_hints,
        theme=context.theme,
        request=context.request,
        show_internal_tree_paths=context.painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(time.time(), tree, str(row["invhist_time"]))
        code = HTML.without_escaping(output_funnel.drain())

    return "invtree", code


def _export_for_python_invhist_delta(
    row: Row, _cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> SDRawDeltaTree:
    return serialize_delta_tree(_compute_data_invhist_delta(row, acting_user, context))


def _export_for_csv_invhist_delta(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def _export_for_json_invhist_delta(
    row: Row, _cell: Cell, acting_user: LoggedInUser, context: PainterContext
) -> SDRawDeltaTree:
    return serialize_delta_tree(_compute_data_invhist_delta(row, acting_user, context))


def make_invhist_delta_painter() -> InternalPainter:
    return InternalPainter(
        ident="invhist_delta",
        title=_l("Inventory changes"),
        columns=["invhist_delta", "invhist_time"],
        painter_options=["show_internal_tree_paths"],
        render=_render_invhist_delta,
        compute_data=_compute_data_invhist_delta,
        export_for_python=_export_for_python_invhist_delta,
        export_for_csv=_export_for_csv_invhist_delta,
        export_for_json=_export_for_json_invhist_delta,
    )


def _paint_invhist_count(row: Row, what: str) -> CellSpec:
    number = row["invhist_" + what]
    if number:
        return "narrow number", str(number)
    return "narrow number unused", "0"


def _render_invhist_removed(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_invhist_count(row, "removed")


def make_invhist_removed_painter() -> InternalPainter:
    return InternalPainter(
        ident="invhist_removed",
        title=_l("Removed entries"),
        short_title=_l("Removed"),
        columns=["invhist_removed"],
        render=_render_invhist_removed,
    )


def _render_invhist_new(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_invhist_count(row, "new")


def make_invhist_new_painter() -> InternalPainter:
    return InternalPainter(
        ident="invhist_new",
        title=_l("New entries"),
        short_title=_l("New"),
        columns=["invhist_new"],
        render=_render_invhist_new,
    )


def _render_invhist_changed(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_invhist_count(row, "changed")


def make_invhist_changed_painter() -> InternalPainter:
    return InternalPainter(
        ident="invhist_changed",
        title=_l("Changed entries"),
        short_title=_l("Changed"),
        columns=["invhist_changed"],
        render=_render_invhist_changed,
    )


def _get_attributes(row: Row, path: SDPath) -> ImmutableAttributes | None:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return None
    return _get_inventory_tree(row).get_tree(path).attributes


def _compute_attribute_painter_data(row: Row, path: SDPath, key: SDKey) -> SDValue:
    if (attributes := _get_attributes(row, path)) is None:
        return None
    return attributes.pairs.get(key)


def _paint_host_inventory_attribute(
    row: Row, path: SDPath, key: SDKey, hint: AttributeDisplayHint, theme: Theme
) -> CellSpec:
    if (attributes := _get_attributes(row, path)) is None:
        return "", ""
    return compute_cell_spec(
        SDItem(
            key=key,
            title=hint.title,
            value=attributes.pairs.get(key),
            retention_interval=attributes.retentions.get(key),
            paint_function=hint.paint_function,
            icon_path_svc_problems=theme.detect_icon_path("svc_problems", "icon_"),
        ).compute_td_spec(time.time()),
        text_align="",
    )


def _render_inventory_attribute(
    path: SDPath,
    key: SDKey,
    hint: AttributeDisplayHint,
    row: Row,
    _cell: Cell,
    _user: LoggedInUser,
    context: PainterContext,
) -> CellSpec:
    if (error_cell := _multiple_trees_cell(row)) is not None:
        return error_cell
    return _paint_host_inventory_attribute(row, path, key, hint, context.theme)


def _export_inventory_attribute(
    path: SDPath, key: SDKey, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> SDValue:
    return _compute_attribute_painter_data(row, path, key)


def _export_inventory_attribute_for_csv(
    path: SDPath, key: SDKey, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return "" if (data := _compute_attribute_painter_data(row, path, key)) is None else str(data)


def _group_by_inventory_attribute(
    path: SDPath,
    key: SDKey,
    hint: AttributeDisplayHint,
    row: Row,
    _cell: Cell,
    context: PainterContext,
) -> str | None:
    painted = _paint_host_inventory_attribute(row, path, key, hint, context.theme)[1]
    return str(painted) if isinstance(painted, str | HTML) else None


def make_inventory_attribute_painter(
    path: SDPath, key: SDKey, hint: AttributeDisplayHint
) -> InternalPainter:
    return InternalPainter(
        ident=hint.name,
        title=hint.long_inventory_title,
        # The short titles (used in column headers) may overlap for different painters, e.g.:
        # - BIOS > Version
        # - Firmware > Version
        # We want to keep column titles short, yet, to make up for overlapping we show the
        # long_title in the column title tooltips
        short_title=hint.short_title,
        tooltip_title=hint.long_title,
        columns=["host_inventory", "host_structured_status"],
        sorter=hint.name,
        printable=True,
        painter_options=["show_internal_tree_paths"],
        load_inv=True,
        parameters=Dictionary(
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
        group_by=partial(_group_by_inventory_attribute, path, key, hint),
        render=partial(_render_inventory_attribute, path, key, hint),
        export_for_python=partial(_export_inventory_attribute, path, key),
        export_for_csv=partial(_export_inventory_attribute_for_csv, path, key),
        export_for_json=partial(_export_inventory_attribute, path, key),
    )


def _paint_host_inventory_column(row: Row, hint: ColumnDisplayHintOfView, theme: Theme) -> CellSpec:
    if hint.name not in row:
        return "", ""
    return compute_cell_spec(
        SDItem(
            key=SDKey(hint.name),
            title=hint.title,
            value=row[hint.name],
            retention_interval=row.get(f"{hint.name}_retention_interval"),
            paint_function=hint.paint_function,
            icon_path_svc_problems=theme.detect_icon_path("svc_problems", "icon_"),
        ).compute_td_spec(time.time()),
        text_align="",
    )


def _render_inventory_column(
    hint: ColumnDisplayHintOfView,
    row: Row,
    _cell: Cell,
    _user: LoggedInUser,
    context: PainterContext,
) -> CellSpec:
    return _paint_host_inventory_column(row, hint, context.theme)


def _export_inventory_column(
    hint: ColumnDisplayHintOfView,
    row: Row,
    _cell: Cell,
    _user: LoggedInUser,
    _context: PainterContext,
) -> object:
    return row.get(hint.name)


def _export_inventory_column_for_csv(
    hint: ColumnDisplayHintOfView,
    row: Row,
    _cell: Cell,
    _user: LoggedInUser,
    _context: PainterContext,
) -> str:
    return "" if (data := row.get(hint.name)) is None else str(data)


def make_inventory_column_painter(hint: ColumnDisplayHintOfView) -> InternalPainter:
    return InternalPainter(
        ident=hint.name,
        title=hint.long_inventory_title,
        # The short titles (used in column headers) may overlap for different painters, e.g.:
        # - BIOS > Version
        # - Firmware > Version
        # We want to keep column titles short, yet, to make up for overlapping we show the
        # long_title in the column title tooltips
        short_title=hint.short_title,
        tooltip_title=hint.long_title,
        columns=[hint.name],
        sorter=hint.name,
        printable=True,
        load_inv=False,
        # See painter/base.py::Cell.painter_parameters
        # We have to add a dummy value here such that the painter_parameters are not None and
        # the "real" parameters, ie. _painter_params, are used.
        parameters=FixedValue(PainterParameters(), totext=""),
        render=partial(_render_inventory_column, hint),
        export_for_python=partial(_export_inventory_column, hint),
        export_for_csv=partial(_export_inventory_column_for_csv, hint),
        export_for_json=partial(_export_inventory_column, hint),
    )


def _compute_node_painter_data(row: Row, path: SDPath) -> ImmutableTree:
    try:
        _validate_inventory_tree_uniqueness(row)
    except MultipleInventoryTreesError:
        return ImmutableTree()

    return _get_inventory_tree(row).get_tree(path)


def _render_inventory_node(
    path: SDPath, row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if (error_cell := _multiple_trees_cell(row)) is not None:
        return error_cell
    if not (tree := _compute_node_painter_data(row, path)):
        return "", ""

    tree_renderer = TreeRenderer(
        site_id=row["site"],
        host_name=row["host_name"],
        hints=inv_display_hints,
        theme=context.theme,
        request=context.request,
        show_internal_tree_paths=context.painter_options.get("show_internal_tree_paths"),
    )

    with output_funnel.plugged():
        tree_renderer.show(time.time(), tree)
        code = HTML.without_escaping(output_funnel.drain())

    return "invtree", code


def _export_inventory_node(
    path: SDPath, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return serialize_tree(_compute_node_painter_data(row, path))


def _export_inventory_node_for_csv(
    _row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str | HTML:
    raise CSVExportError


def make_inventory_node_painter(hint: NodeDisplayHint) -> InternalPainter:
    return InternalPainter(
        ident=hint.name,
        title=hint.long_inventory_title,
        short_title=hint.short_title,
        tooltip_title=hint.long_inventory_title,
        columns=["host_inventory", "host_structured_status"],
        sorter=hint.name,
        # Only attributes can be shown in reports. There is currently no way to render trees.
        # The HTML code would simply be stripped by the default rendering mechanism which does
        # not look good for the HW/SW Inventory tree
        printable=False,
        painter_options=["show_internal_tree_paths"],
        load_inv=True,
        parameters=Dictionary(
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
        render=partial(_render_inventory_node, hint.path),
        export_for_python=partial(_export_inventory_node, hint.path),
        export_for_csv=_export_inventory_node_for_csv,
        export_for_json=partial(_export_inventory_node, hint.path),
    )
