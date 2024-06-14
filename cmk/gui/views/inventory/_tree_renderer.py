#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from functools import total_ordering
from typing import Iterable, NamedTuple

from livestatus import SiteId

import cmk.utils.render
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    ImmutableAttributes,
    ImmutableDeltaAttributes,
    ImmutableDeltaTable,
    ImmutableDeltaTree,
    ImmutableTable,
    ImmutableTree,
    RetentionInterval,
    SDDeltaValue,
    SDKey,
    SDPath,
    SDRowIdent,
    SDValue,
)

from cmk.gui import inventory
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, Request
from cmk.gui.i18n import _
from cmk.gui.utils.html import HTML
from cmk.gui.utils.theme import theme, Theme
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors

from ._display_hints import ColumnDisplayHint, DisplayHints, inv_display_hints, NodeDisplayHint
from .registry import PaintFunction


def make_table_view_name_of_host(view_name: str) -> str:
    return f"{view_name}_of_host"


def _make_columns_and_hints(
    rows: Sequence[Mapping[SDKey, SDValue]] | Sequence[Mapping[SDKey, SDDeltaValue]],
    hint: NodeDisplayHint,
) -> OrderedDict[SDKey, ColumnDisplayHint]:
    return OrderedDict(
        {
            c: hint.get_column_hint(c)
            for c in list(hint.columns) + sorted({k for r in rows for k in r} - set(hint.columns))
        }
    )


@total_ordering
class _MinType:
    def __le__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return self is other


class SDItem(NamedTuple):
    key: SDKey
    value: SDValue
    retention_interval: RetentionInterval | None


def _sort_pairs(attributes: ImmutableAttributes, key_order: Sequence[SDKey]) -> Sequence[SDItem]:
    sorted_keys = list(key_order) + sorted(set(attributes.pairs) - set(key_order))
    return [
        SDItem(k, attributes.pairs[k], attributes.retentions.get(k))
        for k in sorted_keys
        if k in attributes.pairs
    ]


def _sort_rows(table: ImmutableTable, columns: Iterable[SDKey]) -> Sequence[Sequence[SDItem]]:
    def _sort_row(ident: SDRowIdent, row: Mapping[SDKey, SDValue]) -> Sequence[SDItem]:
        return [SDItem(c, row.get(c), table.retentions.get(ident, {}).get(c)) for c in columns]

    min_type = _MinType()

    return [
        _sort_row(ident, row)
        for ident, row in sorted(
            table.rows_by_ident.items(),
            key=lambda t: tuple(t[1].get(c) or min_type for c in columns),
        )
        if not all(v is None for v in row.values())
    ]


class _SDDeltaItem(NamedTuple):
    key: SDKey
    old: SDValue
    new: SDValue


def _sort_delta_pairs(
    attributes: ImmutableDeltaAttributes, key_order: Sequence[SDKey]
) -> Sequence[_SDDeltaItem]:
    sorted_keys = list(key_order) + sorted(set(attributes.pairs) - set(key_order))
    return [
        _SDDeltaItem(k, attributes.pairs[k].old, attributes.pairs[k].new)
        for k in sorted_keys
        if k in attributes.pairs
    ]


def _sort_delta_rows(
    table: ImmutableDeltaTable, columns: Iterable[SDKey]
) -> Sequence[Sequence[_SDDeltaItem]]:
    def _sort_row(row: Mapping[SDKey, SDDeltaValue]) -> Sequence[_SDDeltaItem]:
        return [
            _SDDeltaItem(c, v.old, v.new)
            for c in columns
            for v in (row.get(c) or SDDeltaValue(None, None),)
        ]

    min_type = _MinType()

    def _sanitize(value: SDDeltaValue) -> tuple[_MinType | SDValue, _MinType | SDValue]:
        return (value.old or min_type, value.new or min_type)

    return [
        _sort_row(row)
        for row in sorted(
            table.rows,
            key=lambda r: tuple(_sanitize(r.get(c) or SDDeltaValue(None, None)) for c in columns),
        )
        if not all(left == right for left, right in row.values())
    ]


def compute_cell_spec(
    item: SDItem, paint_function: PaintFunction, icon_path_svc_problems: str
) -> tuple[str, HTML]:
    # TODO separate tdclass from rendered value
    tdclass, code = paint_function(item.value)
    html_value = HTML.with_escaping(code)
    if (
        not html_value
        or item.retention_interval is None
        or item.retention_interval.source == "current"
    ):
        return tdclass, html_value

    now = int(time.time())
    valid_until = item.retention_interval.cached_at + item.retention_interval.cache_interval
    keep_until = valid_until + item.retention_interval.retention_interval
    if now > keep_until:
        return (
            tdclass,
            HTMLWriter.render_span(
                html_value
                + HTMLWriter.render_nbsp()
                + HTMLWriter.render_img(icon_path_svc_problems, class_=["icon"]),
                title=_("Data is outdated and will be removed with the next check execution"),
                css=["muted_text"],
            ),
        )
    if now > valid_until:
        return (
            tdclass,
            HTMLWriter.render_span(
                html_value,
                title=_("Data was provided at %s and is considered valid until %s")
                % (
                    cmk.utils.render.date_and_time(item.retention_interval.cached_at),
                    cmk.utils.render.date_and_time(keep_until),
                ),
                css=["muted_text"],
            ),
        )
    return tdclass, html_value


def _compute_delta_cell_spec(item: _SDDeltaItem, paint_function: PaintFunction) -> tuple[str, HTML]:
    if item.old is None and item.new is not None:
        tdclass, rendered_value = paint_function(item.new)
        return tdclass, HTMLWriter.render_span(rendered_value, css="invnew")
    if item.old is not None and item.new is None:
        tdclass, rendered_value = paint_function(item.old)
        return tdclass, HTMLWriter.render_span(rendered_value, css="invold")
    if item.old == item.new:
        tdclass, rendered_value = paint_function(item.old)
        return tdclass, HTML.with_escaping(rendered_value)
    if item.old is not None and item.new is not None:
        tdclass, rendered_old_value = paint_function(item.old)
        tdclass, rendered_new_value = paint_function(item.new)
        return (
            tdclass,
            HTMLWriter.render_span(rendered_old_value, css="invold")
            + " → "
            + HTMLWriter.render_span(rendered_new_value, css="invnew"),
        )
    raise NotImplementedError()


# Ajax call for fetching parts of the tree
def ajax_inv_render_tree() -> None:
    site_id = SiteId(request.get_ascii_input_mandatory("site"))
    host_name = request.get_validated_type_input_mandatory(HostName, "host")
    inventory.verify_permission(host_name, site_id)

    raw_path = request.get_ascii_input_mandatory("raw_path")
    show_internal_tree_paths = bool(request.var("show_internal_tree_paths"))

    tree: ImmutableTree | ImmutableDeltaTree
    if tree_id := request.get_ascii_input_mandatory("tree_id", ""):
        tree, corrupted_history_files = inventory.load_delta_tree(host_name, int(tree_id))
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _(
                        "Cannot load HW/SW inventory history entries %s."
                        " Please remove the corrupted files."
                    )
                    % ", ".join(corrupted_history_files),
                )
            )
            return
    else:
        row = inventory.get_status_data_via_livestatus(site_id, host_name)
        try:
            tree = inventory.load_filtered_and_merged_tree(row)
        except Exception as e:
            if active_config.debug:
                html.show_warning("%s" % e)
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _("Cannot load HW/SW inventory tree %s. Please remove the corrupted file.")
                    % inventory.get_short_inventory_filepath(host_name),
                )
            )
            return

    inventory_path = inventory.parse_inventory_path(raw_path or "")
    if not (tree := tree.get_tree(inventory_path.path)):
        html.show_error(_("No such tree below %r") % inventory_path.path)
        return

    TreeRenderer(
        site_id,
        host_name,
        inv_display_hints,
        theme,
        request,
        show_internal_tree_paths,
        tree_id,
    ).show(tree)


def _replace_title_placeholders(hint: NodeDisplayHint, path: SDPath) -> str:
    if "%d" not in hint.title and "%s" not in hint.title:
        return hint.title
    title = hint.title.replace("%d", "%s")
    node_names = tuple(path[idx] for idx, node_name in enumerate(hint.path) if node_name == "*")
    return title % node_names[-title.count("%s") :]


class TreeRenderer:
    def __init__(
        self,
        site_id: SiteId,
        hostname: HostName,
        hints: DisplayHints,
        theme_: Theme,
        request_: Request,
        show_internal_tree_paths: bool = False,
        tree_id: str = "",
    ) -> None:
        self._site_id = site_id
        self._hostname = hostname
        self._hints = hints
        self._theme = theme_
        self._request = request_
        self._show_internal_tree_paths = show_internal_tree_paths
        self._tree_id = tree_id
        self._tree_name = f"inv_{hostname}{tree_id}"

    def _get_header(self, title: str, key_info: str) -> HTML:
        # Todo (CMK-17819)
        header = HTML.without_escaping(title)
        if self._show_internal_tree_paths:
            header += " " + HTMLWriter.render_span(f"({key_info})", css="muted_text")
        return header

    def _show_attributes(
        self,
        attributes: ImmutableAttributes | ImmutableDeltaAttributes,
        hint: NodeDisplayHint,
    ) -> None:
        sorted_pairs: Sequence[SDItem] | Sequence[_SDDeltaItem] = (
            _sort_pairs(attributes, list(hint.attributes))
            if isinstance(attributes, ImmutableAttributes)
            else _sort_delta_pairs(attributes, list(hint.attributes))
        )

        html.open_table()
        for item in sorted_pairs:
            attr_hint = hint.get_attribute_hint(item.key)
            html.open_tr()
            html.th(self._get_header(attr_hint.title, item.key))
            html.open_td()
            if isinstance(item, SDItem):
                _tdclass, rendered_value = compute_cell_spec(
                    item,
                    attr_hint.paint_function,
                    self._theme.detect_icon_path("svc_problems", "icon_"),
                )
            else:
                _tdclass, rendered_value = _compute_delta_cell_spec(item, attr_hint.paint_function)
            html.write_html(rendered_value)
            html.close_td()
            html.close_tr()
        html.close_table()

    def _show_table(
        self,
        table: ImmutableTable | ImmutableDeltaTable,
        hint: NodeDisplayHint,
    ) -> None:
        if hint.table_view_name:
            # Link to Multisite view with exactly this table
            html.div(
                HTMLWriter.render_a(
                    _("Open this table for filtering / sorting"),
                    href=makeuri_contextless(
                        self._request,
                        [
                            (
                                "view_name",
                                make_table_view_name_of_host(hint.table_view_name),
                            ),
                            ("host", self._hostname),
                        ],
                        filename="view.py",
                    ),
                ),
                class_="invtablelink",
            )

        columns_and_hints = _make_columns_and_hints(table.rows, hint)
        sorted_rows: Sequence[Sequence[SDItem]] | Sequence[Sequence[_SDDeltaItem]] = (
            _sort_rows(table, columns_and_hints)
            if isinstance(table, ImmutableTable)
            else _sort_delta_rows(table, columns_and_hints)
        )

        # TODO: Use table.open_table() below.
        html.open_table(class_="data")
        html.open_tr()
        for column, col_hint in columns_and_hints.items():
            html.th(
                self._get_header(
                    col_hint.title,
                    f"{column}*" if column in table.key_columns else column,
                )
            )
        html.close_tr()

        for row in sorted_rows:
            html.open_tr(class_="even0")
            for item in row:
                col_hint = columns_and_hints[item.key]
                # TODO separate tdclass from rendered value
                if isinstance(item, SDItem):
                    tdclass, rendered_value = compute_cell_spec(
                        item,
                        col_hint.paint_function,
                        self._theme.detect_icon_path("svc_problems", "icon_"),
                    )
                else:
                    tdclass, rendered_value = _compute_delta_cell_spec(
                        item, col_hint.paint_function
                    )
                html.open_td(class_=tdclass)
                html.write_html(rendered_value)
                html.close_td()
            html.close_tr()
        html.close_table()

    def _show_node(self, node: ImmutableTree | ImmutableDeltaTree) -> None:
        hint = self._hints.get_node_hint(node.path)
        title = self._get_header(
            _replace_title_placeholders(hint, node.path),
            ".".join(map(str, node.path)),
        )
        if hint.icon:
            title += html.render_img(
                class_=(["title", "icon"]),
                src=self._theme.detect_icon_path(hint.icon, "icon_"),
            )
        raw_path = f".{'.'.join(map(str, node.path))}." if node.path else "."
        with foldable_container(
            treename=self._tree_name,
            id_=raw_path,
            isopen=False,
            title=title,
            fetch_url=makeuri_contextless(
                self._request,
                [
                    ("site", self._site_id),
                    ("host", self._hostname),
                    ("raw_path", raw_path),
                    ("show_internal_tree_paths", "on" if self._show_internal_tree_paths else ""),
                    ("tree_id", self._tree_id),
                ],
                "ajax_inv_render_tree.py",
            ),
        ) as is_open:
            if is_open:
                self.show(node)

    def show(self, tree: ImmutableTree | ImmutableDeltaTree) -> None:
        hint = self._hints.get_node_hint(tree.path)
        if tree.attributes:
            self._show_attributes(tree.attributes, hint)
        if tree.table:
            self._show_table(tree.table, hint)
        for _name, node in sorted(tree.nodes_by_name.items(), key=lambda t: t[0]):
            if isinstance(node, (ImmutableTree, ImmutableDeltaTree)):
                # sorted tries to find the common base class, which is object :(
                self._show_node(node)
