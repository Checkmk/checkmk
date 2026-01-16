#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"

import abc
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import total_ordering
from typing import Literal

import cmk.utils.paths
import cmk.utils.render
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import inventory
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.http import request as http_request
from cmk.gui.i18n import _
from cmk.gui.pages import PageContext
from cmk.gui.theme import Theme
from cmk.gui.theme.current_theme import theme as gui_theme
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.inventory.structured_data import (
    HistoryStore,
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

from ._display_hints import (
    DisplayHints,
    inv_display_hints,
    NodeDisplayHint,
    PaintFunctionFromAPI,
    TableWithView,
)


def make_table_view_name_of_host(view_name: str) -> str:
    return f"{view_name}_of_host"


@dataclass(frozen=True, kw_only=True)
class TDSpec:
    css_classes: Sequence[str]
    text_align: str
    background_color: str
    color: str
    html_value: HTML


def compute_cell_spec(td_spec: TDSpec, text_align: Literal["", "left"]) -> tuple[str, HTML]:
    css_classes = list(td_spec.css_classes)
    styles = []
    if text_align:
        styles.append(f"text-align: {text_align};")
    elif td_spec.text_align:
        styles.append(f"text-align: {td_spec.text_align};")
    if td_spec.color:
        styles.append(f"color: {td_spec.color};")
    if td_spec.background_color:
        css_classes.append("inv_cell_no_padding")
        styles.extend(
            [
                f"background-color: {td_spec.background_color};",
                "height: 100%;",
                "display: flex;",
                "align-items: center;",
                "justify-content: center;",
            ]
        )
    return (
        " ".join(css_classes),
        (
            HTMLWriter.render_div(td_spec.html_value, style=" ".join(styles))
            if styles
            else td_spec.html_value
        ),
    )


@dataclass(frozen=True, kw_only=True)
class SDItem:
    key: SDKey
    title: str
    value: SDValue
    retention_interval: RetentionInterval | None
    paint_function: PaintFunctionFromAPI
    icon_path_svc_problems: str

    def compute_td_spec(self, now: float) -> TDSpec:
        td_styles, rendered_value = self.paint_function(now, self.value)
        html_value = HTML.with_escaping(rendered_value)
        if (
            not html_value
            or self.retention_interval is None
            or self.retention_interval.source == "current"
        ):
            return TDSpec(
                css_classes=[td_styles.css_class] if td_styles.css_class else [],
                text_align=td_styles.text_align,
                background_color=td_styles.background_color,
                color=td_styles.color,
                html_value=html_value,
            )

        valid_until = self.retention_interval.cached_at + self.retention_interval.cache_interval
        keep_until = valid_until + self.retention_interval.retention_interval
        if now > keep_until:
            return TDSpec(
                css_classes=(
                    [td_styles.css_class, "inactive_cell"]
                    if td_styles.css_class
                    else ["inactive_cell"]
                ),
                text_align=td_styles.text_align,
                background_color=td_styles.background_color,
                color=td_styles.color,
                html_value=HTMLWriter.render_span(
                    html_value
                    + HTMLWriter.render_nbsp()
                    + HTMLWriter.render_img(self.icon_path_svc_problems, class_=["icon"]),
                    title=_("Data is outdated and will be removed with the next check execution"),
                    css=["muted_text"],
                ),
            )

        if now > valid_until:
            return TDSpec(
                css_classes=(
                    [td_styles.css_class, "inactive_cell"]
                    if td_styles.css_class
                    else ["inactive_cell"]
                ),
                text_align=td_styles.text_align,
                background_color=td_styles.background_color,
                color=td_styles.color,
                html_value=HTMLWriter.render_span(
                    html_value,
                    title=_("Data was provided at %s and is considered valid until %s")
                    % (
                        cmk.utils.render.date_and_time(self.retention_interval.cached_at),
                        cmk.utils.render.date_and_time(keep_until),
                    ),
                    css=["muted_text"],
                ),
            )

        return TDSpec(
            css_classes=[td_styles.css_class] if td_styles.css_class else [],
            text_align=td_styles.text_align,
            background_color=td_styles.background_color,
            color=td_styles.color,
            html_value=html_value,
        )


@dataclass(frozen=True, kw_only=True)
class _SDDeltaItem:
    key: SDKey
    title: str
    old: SDValue
    new: SDValue
    paint_function: PaintFunctionFromAPI

    def compute_td_spec(self, now: float) -> TDSpec:
        if self.old is None and self.new is not None:
            td_styles, rendered_value = self.paint_function(now, self.new)
            return TDSpec(
                css_classes=[td_styles.css_class] if td_styles.css_class else [],
                text_align="",
                background_color="",
                color="",
                html_value=HTMLWriter.render_span(rendered_value, css="invnew"),
            )

        if self.old is not None and self.new is None:
            td_styles, rendered_value = self.paint_function(now, self.old)
            return TDSpec(
                css_classes=[td_styles.css_class] if td_styles.css_class else [],
                text_align="",
                background_color="",
                color="",
                html_value=HTMLWriter.render_span(rendered_value, css="invold"),
            )

        if self.old == self.new:
            td_styles, rendered_value = self.paint_function(now, self.old)
            return TDSpec(
                css_classes=[td_styles.css_class] if td_styles.css_class else [],
                text_align="",
                background_color="",
                color="",
                html_value=HTML.with_escaping(rendered_value),
            )

        if self.old is not None and self.new is not None:
            _td_styles, rendered_old_value = self.paint_function(now, self.old)
            td_styles, rendered_new_value = self.paint_function(now, self.new)
            return TDSpec(
                css_classes=[td_styles.css_class] if td_styles.css_class else [],
                text_align="",
                background_color="",
                color="",
                html_value=(
                    HTMLWriter.render_span(rendered_old_value, css="invold")
                    + " → "
                    + HTMLWriter.render_span(rendered_new_value, css="invnew")
                ),
            )

        raise NotImplementedError()


@dataclass(frozen=True, kw_only=True)
class _Column:
    key: SDKey
    title: str
    paint_function: PaintFunctionFromAPI
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
            for c in (
                list(self.hint.table.columns) + sorted(needed_keys - set(self.hint.table.columns))
            )
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
def ajax_inv_render_tree(ctx: PageContext) -> None:
    site_id = SiteId(http_request.get_ascii_input_mandatory("site"))
    host_name = http_request.get_validated_type_input_mandatory(HostName, "host")
    inventory.verify_permission(site_id, host_name)

    raw_path = http_request.get_ascii_input_mandatory("raw_path", "")
    show_internal_tree_paths = bool(http_request.var("show_internal_tree_paths"))

    tree: ImmutableTree | ImmutableDeltaTree
    if tree_id := http_request.get_ascii_input_mandatory("tree_id", ""):
        tree, corrupted_history_files = inventory.load_delta_tree(
            HistoryStore(cmk.utils.paths.omd_root),
            host_name,
            int(tree_id),
        )
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _(
                        "Cannot load HW/SW inventory history of %s. Please remove the corrupted files %s."
                    )
                    % (host_name, ", ".join(corrupted_history_files)),
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
            if ctx.config.debug:
                html.show_warning("%s" % e)
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _(
                        "Cannot load HW/SW inventory of %s. Please remove the corrupted inventory or status data tree files."
                    )
                    % host_name,
                )
            )
            return

    TreeRenderer(
        site_id=site_id,
        host_name=host_name,
        hints=inv_display_hints,
        theme=gui_theme,
        request=http_request,
        show_internal_tree_paths=show_internal_tree_paths,
    ).show(time.time(), tree.get_tree(inventory.parse_internal_raw_path(raw_path).path), tree_id)


def _replace_title_placeholders(hint: NodeDisplayHint, path: SDPath) -> str:
    if "%d" not in hint.title and "%s" not in hint.title:
        return hint.title
    title = hint.title.replace("%d", "%s")
    node_names = tuple(path[idx] for idx, node_name in enumerate(hint.path) if node_name == "*")
    return title % node_names[-title.count("%s") :]


class TreeRenderer:
    def __init__(
        self,
        *,
        site_id: SiteId,
        host_name: HostName,
        hints: DisplayHints,
        theme: Theme,
        request: Request,
        show_internal_tree_paths: bool,
    ) -> None:
        self._site_id = site_id
        self._host_name = host_name
        self._hints = hints
        self._theme = theme
        self._request = request
        self._show_internal_tree_paths = show_internal_tree_paths

    def _get_header(self, title: str, key_info: str) -> HTML:
        header = HTML.with_escaping(title)
        if self._show_internal_tree_paths:
            header += " " + HTMLWriter.render_span(f"({key_info})", css="muted_text")
        return header

    def _show_attributes(
        self, now: float, sorted_pairs: Sequence[SDItem] | Sequence[_SDDeltaItem]
    ) -> None:
        html.open_table()
        for item in sorted_pairs:
            html.open_tr()
            html.th(self._get_header(item.title, item.key))
            css_class, html_value = compute_cell_spec(item.compute_td_spec(now), text_align="left")
            if css_class:
                html.open_td(class_=css_class)
            else:
                html.open_td()
            html.write_html(html_value)
            html.close_td()
            html.close_tr()
        html.close_table()

    def _show_table(
        self,
        now: float,
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
                css_class, html_value = compute_cell_spec(item.compute_td_spec(now), text_align="")
                if css_class:
                    html.open_td(class_=css_class)
                else:
                    html.open_td()
                html.write_html(html_value)
                html.close_td()
            html.close_tr()
        html.close_table()

    def _show_node(
        self, now: float, node: ImmutableTree | ImmutableDeltaTree, tree_id: str
    ) -> None:
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
                self.show(now, node)

    def show(self, now: float, tree: ImmutableTree | ImmutableDeltaTree, tree_id: str = "") -> None:
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
            self._show_attributes(now, sorted_pairs)
        if sorted_rows:
            self._show_table(
                now,
                hint.table.name if isinstance(hint.table, TableWithView) else "",
                columns,
                sorted_rows,
            )
        for name in sorted(tree.nodes_by_name):
            self._show_node(now, tree.nodes_by_name[name], tree_id)
