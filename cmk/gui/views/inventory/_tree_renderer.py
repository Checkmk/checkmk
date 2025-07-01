#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import total_ordering
from typing import Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

import cmk.utils.paths
import cmk.utils.render
from cmk.utils.structured_data import (
    ImmutableAttributes,
    ImmutableDeltaAttributes,
    ImmutableDeltaTable,
    ImmutableDeltaTree,
    ImmutableTable,
    ImmutableTree,
    InventoryStore,
    RetentionInterval,
    SDDeltaValue,
    SDKey,
    SDPath,
    SDRowIdent,
    SDValue,
)

from cmk.gui import inventory
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.theme import Theme
from cmk.gui.theme.current_theme import theme
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors

from ._display_hints import DisplayHints, inv_display_hints, NodeDisplayHint
from .registry import PaintFunction


def make_table_view_name_of_host(view_name: str) -> str:
    return f"{view_name}_of_host"


@dataclass(frozen=True, kw_only=True)
class SDItem:
    key: SDKey
    title: str
    value: SDValue
    retention_interval: RetentionInterval | None
    paint_function: PaintFunction
    icon_path_svc_problems: str

    def compute_cell_spec(self) -> tuple[str, Literal["", "inactive_cell"], HTML]:
        # Returns a tuple of two css classes (alignment and coloring) and the HTML value
        # We keep alignment and coloring classes separate as we only need the coloring within
        # tables
        alignment_class, code = self.paint_function(self.value)
        html_value = HTML.with_escaping(code)
        if (
            not html_value
            or self.retention_interval is None
            or self.retention_interval.source == "current"
        ):
            return alignment_class, "", html_value

        now = int(time.time())
        valid_until = self.retention_interval.cached_at + self.retention_interval.cache_interval
        keep_until = valid_until + self.retention_interval.retention_interval
        if now > keep_until:
            return (
                alignment_class,
                "inactive_cell",
                HTMLWriter.render_span(
                    html_value
                    + HTMLWriter.render_nbsp()
                    + HTMLWriter.render_img(self.icon_path_svc_problems, class_=["icon"]),
                    title=_("Data is outdated and will be removed with the next check execution"),
                    css=["muted_text"],
                ),
            )
        if now > valid_until:
            return (
                alignment_class,
                "inactive_cell",
                HTMLWriter.render_span(
                    html_value,
                    title=_("Data was provided at %s and is considered valid until %s")
                    % (
                        cmk.utils.render.date_and_time(self.retention_interval.cached_at),
                        cmk.utils.render.date_and_time(keep_until),
                    ),
                    css=["muted_text"],
                ),
            )
        return alignment_class, "", html_value


@dataclass(frozen=True, kw_only=True)
class _SDDeltaItem:
    key: SDKey
    title: str
    old: SDValue
    new: SDValue
    paint_function: PaintFunction

    def compute_cell_spec(self) -> tuple[str, Literal["", "inactive_cell"], HTML]:
        # Returns a tuple of two css classes (alignment and coloring) and the HTML value
        # The coloring class is always an empty string but was added for a consistent fct signature
        # between _SDDeltaItem and SDItem
        if self.old is None and self.new is not None:
            alignment_class, rendered_value = self.paint_function(self.new)
            return (
                alignment_class,
                "",
                HTMLWriter.render_span(rendered_value, css="invnew"),
            )
        if self.old is not None and self.new is None:
            alignment_class, rendered_value = self.paint_function(self.old)
            return (
                alignment_class,
                "",
                HTMLWriter.render_span(rendered_value, css="invold"),
            )
        if self.old == self.new:
            alignment_class, rendered_value = self.paint_function(self.old)
            return alignment_class, "", HTML.with_escaping(rendered_value)
        if self.old is not None and self.new is not None:
            _, rendered_old_value = self.paint_function(self.old)
            alignment_class, rendered_new_value = self.paint_function(self.new)
            return (
                alignment_class,
                "",
                HTMLWriter.render_span(rendered_old_value, css="invold")
                + " → "
                + HTMLWriter.render_span(rendered_new_value, css="invnew"),
            )
        raise NotImplementedError()


@dataclass(frozen=True, kw_only=True)
class _Column:
    key: SDKey
    title: str
    paint_function: PaintFunction
    key_info: str


@total_ordering
class _MinType:
    def __le__(self, other: object) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return self is other


@dataclass(frozen=True)
class _ABCItemsSorter(abc.ABC):
    hint: NodeDisplayHint

    def _make_columns(
        self, keys: Iterable[SDKey], key_columns: Sequence[SDKey]
    ) -> Sequence[_Column]:
        # Always take key columns into account because they identify a row
        needed_keys = set(keys).union(key_columns)
        return [
            _Column(
                key=c,
                title=h.title,
                paint_function=h.paint_function,
                key_info=f"{c}*" if c in key_columns else c,
            )
            for c in list(self.hint.columns) + sorted(needed_keys - set(self.hint.columns))
            if c in needed_keys
            for h in (self.hint.get_column_hint(c),)
        ]


@dataclass(frozen=True)
class _SDItemsSorter(_ABCItemsSorter):
    icon_path_svc_problems: str
    attributes: ImmutableAttributes
    table: ImmutableTable

    def sort_pairs(self) -> Sequence[SDItem]:
        sorted_keys = list(self.hint.attributes) + sorted(
            set(self.attributes.pairs) - set(self.hint.attributes)
        )
        return [
            SDItem(
                key=k,
                title=h.title,
                value=self.attributes.pairs[k],
                retention_interval=self.attributes.retentions.get(k),
                paint_function=h.paint_function,
                icon_path_svc_problems=self.icon_path_svc_problems,
            )
            for k in sorted_keys
            if k in self.attributes.pairs
            for h in (self.hint.get_attribute_hint(k),)
        ]

    def _filter_row_keys(self) -> Iterator[SDKey]:
        for row in self.table.rows:
            for key, value in row.items():
                if value is not None:
                    yield key

    def sort_rows(self) -> tuple[Sequence[_Column], Sequence[Sequence[SDItem]]]:
        columns = self._make_columns(self._filter_row_keys(), self.table.key_columns)

        def _sort_row(ident: SDRowIdent, row: Mapping[SDKey, SDValue]) -> Sequence[SDItem]:
            return [
                SDItem(
                    key=c.key,
                    title=c.title,
                    value=row.get(c.key),
                    retention_interval=self.table.retentions.get(ident, {}).get(c.key),
                    paint_function=c.paint_function,
                    icon_path_svc_problems=self.icon_path_svc_problems,
                )
                for c in columns
            ]

        min_type = _MinType()

        return (
            columns,
            [
                _sort_row(ident, row)
                for ident, row in sorted(
                    self.table.rows_by_ident.items(),
                    key=lambda t: tuple(t[1].get(c.key) or min_type for c in columns),
                )
                if not all(v is None for v in row.values())
            ],
        )


def _delta_value_has_change(delta_value: SDDeltaValue) -> bool:
    return (
        not (delta_value.old is None and delta_value.new is None)
        and delta_value.old != delta_value.new
    )


@dataclass(frozen=True)
class _SDDeltaItemsSorter(_ABCItemsSorter):
    attributes: ImmutableDeltaAttributes
    table: ImmutableDeltaTable

    def sort_pairs(self) -> Sequence[_SDDeltaItem]:
        sorted_keys = list(self.hint.attributes) + sorted(
            set(self.attributes.pairs) - set(self.hint.attributes)
        )
        return [
            _SDDeltaItem(
                key=k,
                title=h.title,
                old=self.attributes.pairs[k].old,
                new=self.attributes.pairs[k].new,
                paint_function=h.paint_function,
            )
            for k in sorted_keys
            if (v := self.attributes.pairs.get(k)) is not None and _delta_value_has_change(v)
            for h in (self.hint.get_attribute_hint(k),)
        ]

    def _filter_delta_row_keys(self) -> Iterator[SDKey]:
        for row in self.table.rows:
            if any(_delta_value_has_change(delta_value) for delta_value in row.values()):
                yield from row

    def sort_rows(self) -> tuple[Sequence[_Column], Sequence[Sequence[_SDDeltaItem]]]:
        columns = self._make_columns(self._filter_delta_row_keys(), self.table.key_columns)

        def _sort_row(row: Mapping[SDKey, SDDeltaValue]) -> Sequence[_SDDeltaItem]:
            return [
                _SDDeltaItem(
                    key=c.key,
                    title=c.title,
                    old=v.old,
                    new=v.new,
                    paint_function=c.paint_function,
                )
                for c in columns
                for v in (row.get(c.key) or SDDeltaValue(old=None, new=None),)
            ]

        min_type = _MinType()

        def _sanitize(
            value: SDDeltaValue,
        ) -> tuple[_MinType | SDValue, _MinType | SDValue]:
            return (value.old or min_type, value.new or min_type)

        return (
            columns,
            [
                _sort_row(row)
                for row in sorted(
                    self.table.rows,
                    key=lambda r: tuple(
                        _sanitize(r.get(c.key) or SDDeltaValue(old=None, new=None)) for c in columns
                    ),
                )
                if any(_delta_value_has_change(delta_value) for delta_value in row.values())
            ],
        )


# Ajax call for fetching parts of the tree
def ajax_inv_render_tree(config: Config) -> None:
    site_id = SiteId(request.get_ascii_input_mandatory("site"))
    host_name = request.get_validated_type_input_mandatory(HostName, "host")
    inventory.verify_permission(site_id, host_name)

    raw_path = request.get_ascii_input_mandatory("raw_path", "")
    show_internal_tree_paths = bool(request.var("show_internal_tree_paths"))

    tree: ImmutableTree | ImmutableDeltaTree
    if tree_id := request.get_ascii_input_mandatory("tree_id", ""):
        tree, corrupted_history_files = inventory.load_delta_tree(
            InventoryStore(cmk.utils.paths.omd_root),
            host_name,
            int(tree_id),
        )
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _("Cannot load HW/SW Inventory history %s. Please remove the corrupted files.")
                    % ", ".join(corrupted_history_files),
                )
            )
            return
    else:
        raw_status_data_tree = inventory.get_raw_status_data_via_livestatus(site_id, host_name)
        try:
            tree = inventory.load_tree(
                host_name=host_name,
                raw_status_data_tree=raw_status_data_tree,
            )
        except Exception as e:
            if config.debug:
                html.show_warning("%s" % e)
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _("Cannot load HW/SW Inventory tree %s. Please remove the corrupted file.")
                    % inventory.get_short_inventory_filepath(host_name),
                )
            )
            return

    TreeRenderer(
        site_id,
        host_name,
        inv_display_hints,
        theme,
        request,
        show_internal_tree_paths,
    ).show(tree.get_tree(inventory.parse_internal_raw_path(raw_path).path), tree_id)


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
        host_name: HostName,
        hints: DisplayHints,
        theme_: Theme,
        request_: Request,
        show_internal_tree_paths: bool,
    ) -> None:
        self._site_id = site_id
        self._host_name = host_name
        self._hints = hints
        self._theme = theme_
        self._request = request_
        self._show_internal_tree_paths = show_internal_tree_paths

    def _get_header(self, title: str, key_info: str) -> HTML:
        header = HTML.with_escaping(title)
        if self._show_internal_tree_paths:
            header += " " + HTMLWriter.render_span(f"({key_info})", css="muted_text")
        return header

    def _show_attributes(self, sorted_pairs: Sequence[SDItem] | Sequence[_SDDeltaItem]) -> None:
        html.open_table()
        for item in sorted_pairs:
            html.open_tr()
            html.th(self._get_header(item.title, item.key))

            # TODO separate alignment_class and coloring_class from rendered value
            _alignment_class, coloring_class, rendered_value = item.compute_cell_spec()
            html.open_td(class_=coloring_class)
            html.write_html(rendered_value)
            html.close_td()
            html.close_tr()
        html.close_table()

    def _show_table(
        self,
        table_view_name: str,
        columns: Sequence[_Column],
        sorted_rows: Sequence[Sequence[SDItem]] | Sequence[Sequence[_SDDeltaItem]],
    ) -> None:
        if table_view_name:
            # Link to Multisite view with exactly this table
            html.div(
                HTMLWriter.render_a(
                    _("Open this table for filtering / sorting"),
                    href=makeuri_contextless(
                        self._request,
                        [
                            (
                                "view_name",
                                make_table_view_name_of_host(table_view_name),
                            ),
                            ("host", self._host_name),
                        ],
                        filename="view.py",
                    ),
                ),
                class_="invtablelink",
            )

        # TODO: Use table.open_table() below.
        html.open_table(class_="data")
        html.open_tr()
        for column in columns:
            html.th(self._get_header(column.title, column.key_info))
        html.close_tr()

        for row in sorted_rows:
            html.open_tr(class_="even0")
            for item in row:
                # TODO separate alignment_class and coloring_class from rendered value
                alignment_class, coloring_class, rendered_value = item.compute_cell_spec()
                html.open_td(class_=" ".join([alignment_class, coloring_class]))
                html.write_html(rendered_value)
                html.close_td()
            html.close_tr()
        html.close_table()

    def _show_node(self, node: ImmutableTree | ImmutableDeltaTree, tree_id: str) -> None:
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
            treename=f"inv_{self._host_name}{tree_id}",
            id_=raw_path,
            isopen=False,
            title=title,
            fetch_url=makeuri_contextless(
                self._request,
                [
                    ("site", self._site_id),
                    ("host", self._host_name),
                    ("raw_path", raw_path),
                    (
                        "show_internal_tree_paths",
                        "on" if self._show_internal_tree_paths else "",
                    ),
                    ("tree_id", tree_id),
                ],
                "ajax_inv_render_tree.py",
            ),
        ) as is_open:
            if is_open:
                self.show(node)

    def show(self, tree: ImmutableTree | ImmutableDeltaTree, tree_id: str = "") -> None:
        hint = self._hints.get_node_hint(tree.path)

        sorted_pairs: Sequence[SDItem] | Sequence[_SDDeltaItem]
        sorted_rows: Sequence[Sequence[SDItem]] | Sequence[Sequence[_SDDeltaItem]]
        match tree:
            case ImmutableTree():
                items_sorter = _SDItemsSorter(
                    hint,
                    self._theme.detect_icon_path("svc_problems", "icon_"),
                    tree.attributes,
                    tree.table,
                )
                sorted_pairs = items_sorter.sort_pairs()
                columns, sorted_rows = items_sorter.sort_rows()
            case ImmutableDeltaTree():
                delta_items_sorter = _SDDeltaItemsSorter(
                    hint,
                    tree.attributes,
                    tree.table,
                )
                sorted_pairs = delta_items_sorter.sort_pairs()
                columns, sorted_rows = delta_items_sorter.sort_rows()

        if sorted_pairs:
            self._show_attributes(sorted_pairs)
        if sorted_rows:
            self._show_table(hint.table_view_name, columns, sorted_rows)
        for name in sorted(tree.nodes_by_name):
            self._show_node(tree.nodes_by_name[name], tree_id)
