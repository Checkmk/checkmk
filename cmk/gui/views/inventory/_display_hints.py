#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from cmk.utils.structured_data import SDKey, SDNodeName, SDPath

import cmk.gui.inventory as inventory
from cmk.gui.i18n import _, _l
from cmk.gui.inventory.filters import (
    FilterInvBool,
    FilterInvFloat,
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableIntegerRange,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableText,
    FilterInvtableTimestampAsAge,
    FilterInvtableVersion,
    FilterInvText,
)

from .registry import inv_paint_funtions, InventoryHintSpec, InvValue, PaintFunction, SortFunction

PAINT_FUNCTION_NAME_PREFIX = "inv_paint_"


def _get_paint_function(raw_hint: InventoryHintSpec) -> tuple[str, PaintFunction]:
    # FIXME At the moment  we need it to get tdclass: Clean this up one day.
    if "paint" in raw_hint:
        data_type = raw_hint["paint"]
        return data_type, inv_paint_funtions[PAINT_FUNCTION_NAME_PREFIX + data_type]["func"]
    return "str", inv_paint_funtions["inv_paint_generic"]["func"]


def _make_sort_function(raw_hint: InventoryHintSpec) -> SortFunction:
    return _decorate_sort_function(raw_hint.get("sort", _cmp_inv_generic))


def _decorate_sort_function(sort_function: SortFunction) -> SortFunction:
    def wrapper(val_a: InvValue | None, val_b: InvValue | None) -> int:
        if val_a is None:
            return 0 if val_b is None else -1

        if val_b is None:
            return 0 if val_a is None else 1

        return sort_function(val_a, val_b)

    return wrapper


def _cmp_inv_generic(val_a: InvValue, val_b: InvValue) -> int:
    return (val_a > val_b) - (val_a < val_b)


def _make_title_function(raw_hint: InventoryHintSpec) -> Callable[[str], str]:
    if "title" not in raw_hint:
        return lambda word: word.replace("_", " ").title()

    if callable(title := raw_hint["title"]):
        # TODO Do we still need this?
        return title

    return lambda word: str(title)


def _make_long_title_function(title: str, parent_path: SDPath) -> Callable[[], str]:
    return lambda: (
        DISPLAY_HINTS.get_tree_hints(parent_path).node_hint.title + " ➤ " + title
        if parent_path
        else title
    )


def _make_ident(path: SDPath, key: str = "") -> str:
    parts = ["inv"] + list(path)
    if key:
        parts.append(key)
    return "_".join(parts)


@dataclass(frozen=True)
class NodeDisplayHint:
    path: SDPath
    title: str
    short_title: str
    _long_title_function: Callable[[], str]
    icon: str

    @property
    def ident(self) -> str:
        return _make_ident(self.path)

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory node: %s") % self.long_title

    @classmethod
    def from_raw(cls, path: SDPath, raw_hint: InventoryHintSpec) -> NodeDisplayHint:
        title = _make_title_function(raw_hint)(path[-1] if path else "")
        return cls(
            path=path,
            title=title,
            short_title=title,
            _long_title_function=_make_long_title_function(title, path[:-1]),
            icon=raw_hint.get("icon", ""),
        )


def _parse_column_display_hint_filter_class(
    filter_class: (
        None
        | type[FilterInvText]
        | type[FilterInvBool]
        | type[FilterInvFloat]
        | type[FilterInvtableAdminStatus]
        | type[FilterInvtableAvailable]
        | type[FilterInvtableIntegerRange]
        | type[FilterInvtableInterfaceType]
        | type[FilterInvtableOperStatus]
        | type[FilterInvtableText]
        | type[FilterInvtableTimestampAsAge]
        | type[FilterInvtableVersion]
    ),
) -> (
    type[FilterInvtableAdminStatus]
    | type[FilterInvtableAvailable]
    | type[FilterInvtableIntegerRange]
    | type[FilterInvtableInterfaceType]
    | type[FilterInvtableOperStatus]
    | type[FilterInvtableText]
    | type[FilterInvtableTimestampAsAge]
    | type[FilterInvtableVersion]
):
    if not filter_class:
        return FilterInvtableText
    match filter_class.__name__:
        case "FilterInvtableAdminStatus":
            return FilterInvtableAdminStatus
        case "FilterInvtableAvailable":
            return FilterInvtableAvailable
        case "FilterInvtableIntegerRange":
            return FilterInvtableIntegerRange
        case "FilterInvtableInterfaceType":
            return FilterInvtableInterfaceType
        case "FilterInvtableOperStatus":
            return FilterInvtableOperStatus
        case "FilterInvtableText":
            return FilterInvtableText
        case "FilterInvtableTimestampAsAge":
            return FilterInvtableTimestampAsAge
        case "FilterInvtableVersion":
            return FilterInvtableVersion
    raise TypeError(filter_class)


@dataclass(frozen=True)
class ColumnDisplayHint:
    view_name: str
    key: SDKey
    title: str
    short_title: str
    _long_title_function: Callable[[], str]
    paint_function: PaintFunction
    sort_function: SortFunction
    filter_class: (
        type[FilterInvtableAdminStatus]
        | type[FilterInvtableAvailable]
        | type[FilterInvtableIntegerRange]
        | type[FilterInvtableInterfaceType]
        | type[FilterInvtableOperStatus]
        | type[FilterInvtableText]
        | type[FilterInvtableTimestampAsAge]
        | type[FilterInvtableVersion]
    )

    @property
    def ident(self) -> str:
        if not self.view_name:
            raise ValueError()
        return f"{self.view_name}_{self.key}"

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory column: %s") % self.long_title

    @classmethod
    def from_raw(
        cls, view_name: str, path: SDPath, key: str, raw_hint: InventoryHintSpec
    ) -> ColumnDisplayHint:
        _data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            view_name=view_name,
            key=SDKey(key),
            title=title,
            short_title=(
                title if (short_title := raw_hint.get("short")) is None else str(short_title)
            ),
            _long_title_function=_make_long_title_function(title, path),
            paint_function=paint_function,
            sort_function=_make_sort_function(raw_hint),
            filter_class=_parse_column_display_hint_filter_class(raw_hint.get("filter")),
        )

    def make_filter(
        self,
    ) -> (
        FilterInvtableAdminStatus
        | FilterInvtableAvailable
        | FilterInvtableIntegerRange
        | FilterInvtableInterfaceType
        | FilterInvtableOperStatus
        | FilterInvtableText
        | FilterInvtableTimestampAsAge
        | FilterInvtableVersion
    ):
        return self.filter_class(
            inv_info=self.view_name,
            ident=self.ident,
            title=self.long_title,
        )


def _parse_view_name(view_name: str | None) -> str:
    if not view_name:
        return ""
    if not view_name.startswith("inv"):
        view_name = f"inv{view_name}"
    if view_name.endswith("_of_host"):
        view_name = view_name[:-8]
    return view_name


@dataclass(frozen=True)
class TableDisplayHint:
    title: str
    _long_title_function: Callable[[], str]
    icon: str
    is_show_more: bool
    view_name: str
    by_column: OrderedDict[str, ColumnDisplayHint]

    @classmethod
    def from_raw(
        cls,
        path: SDPath,
        raw_hint: InventoryHintSpec,
        key_order: Sequence[str],
        by_column: dict[str, InventoryHintSpec],
    ) -> TableDisplayHint:
        title = _make_title_function(raw_hint)(path[-1] if path else "")
        view_name = "" if "*" in path else _parse_view_name(raw_hint.get("view"))
        return cls(
            title=title,
            _long_title_function=_make_long_title_function(title, path[:-1]),
            icon=raw_hint.get("icon", ""),
            is_show_more=raw_hint.get("is_show_more", True),
            # See DYNAMIC-PATHS
            view_name=view_name,
            by_column=OrderedDict(
                {
                    key: ColumnDisplayHint.from_raw(
                        view_name,
                        path,
                        key,
                        by_column.get(key, {}),
                    )
                    for key in key_order
                }
            ),
        )

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory table: %s") % self.long_title


@dataclass(frozen=True)
class AttributeDisplayHint:
    path: SDPath
    key: SDKey
    title: str
    short_title: str
    _long_title_function: Callable[[], str]
    data_type: str
    paint_function: PaintFunction
    sort_function: SortFunction
    is_show_more: bool

    @property
    def ident(self) -> str:
        return _make_ident(self.path, self.key)

    @property
    def long_title(self) -> str:
        return self._long_title_function()

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory attribute: %s") % self.long_title

    @classmethod
    def from_raw(cls, path: SDPath, key: str, raw_hint: InventoryHintSpec) -> AttributeDisplayHint:
        data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            path=path,
            key=SDKey(key),
            title=title,
            short_title=(
                title if (short_title := raw_hint.get("short")) is None else str(short_title)
            ),
            _long_title_function=_make_long_title_function(title, path),
            data_type=data_type,
            paint_function=paint_function,
            sort_function=_make_sort_function(raw_hint),
            is_show_more=raw_hint.get("is_show_more", True),
        )

    def make_filter(self) -> FilterInvText | FilterInvBool | FilterInvFloat:
        inventory_path = inventory.InventoryPath(
            path=self.path,
            source=inventory.TreeSource.attributes,
            key=self.key,
        )
        if self.data_type == "str":
            return FilterInvText(
                ident=self.ident,
                title=self.long_title,
                inventory_path=inventory_path,
                is_show_more=self.is_show_more,
            )

        if self.data_type == "bool":
            return FilterInvBool(
                ident=self.ident,
                title=self.long_title,
                inventory_path=inventory_path,
                is_show_more=self.is_show_more,
            )

        match self.data_type:
            case "bytes" | "bytes_rounded":
                unit = _("MB")
                scale = 1024 * 1024
            case "hz":
                unit = _("MHz")
                scale = 1000000
            case "volt":
                unit = _("Volt")
                scale = 1
            case "timestamp":
                unit = _("secs")
                scale = 1
            case _:
                unit = ""
                scale = 1

        return FilterInvFloat(
            ident=self.ident,
            title=self.long_title,
            inventory_path=inventory_path,
            unit=unit,
            scale=scale,
            is_show_more=self.is_show_more,
        )


@dataclass(frozen=True)
class AttributesDisplayHint:
    by_key: OrderedDict[str, AttributeDisplayHint]


@dataclass(frozen=True)
class _RelatedRawHints:
    for_node: InventoryHintSpec = field(
        default_factory=lambda: InventoryHintSpec()  # pylint: disable=unnecessary-lambda
    )
    for_table: InventoryHintSpec = field(
        default_factory=lambda: InventoryHintSpec()  # pylint: disable=unnecessary-lambda
    )
    by_column: dict[str, InventoryHintSpec] = field(default_factory=dict)
    by_key: dict[str, InventoryHintSpec] = field(default_factory=dict)


def _get_related_raw_hints(
    raw_hints: Mapping[str, InventoryHintSpec]
) -> Mapping[SDPath, _RelatedRawHints]:
    related_raw_hints_by_path: dict[SDPath, _RelatedRawHints] = {}
    for raw_path, raw_hint in raw_hints.items():
        inventory_path = inventory.InventoryPath.parse(raw_path)
        related_raw_hints = related_raw_hints_by_path.setdefault(
            inventory_path.path,
            _RelatedRawHints(),
        )

        if inventory_path.source == inventory.TreeSource.node:
            related_raw_hints.for_node.update(raw_hint)
            continue

        if inventory_path.source == inventory.TreeSource.table:
            if inventory_path.key:
                related_raw_hints.by_column.setdefault(inventory_path.key, raw_hint)
                continue

            related_raw_hints.for_table.update(raw_hint)
            continue

        if inventory_path.source == inventory.TreeSource.attributes and inventory_path.key:
            related_raw_hints.by_key.setdefault(inventory_path.key, raw_hint)
            continue

    return related_raw_hints_by_path


def _complete_key_order(key_order: Sequence[str], additional_keys: set[str]) -> Sequence[str]:
    return list(key_order) + [key for key in sorted(additional_keys) if key not in key_order]


# TODO Workaround for InventoryHintSpec (TypedDict)
# https://github.com/python/mypy/issues/7178
_ALLOWED_KEYS: Sequence[
    Literal[
        "title",
        "short",
        "icon",
        "paint",
        "view",
        "keyorder",
        "sort",
        "filter",
        "is_show_more",
    ]
] = [
    "title",
    "short",
    "icon",
    "paint",
    "view",
    "keyorder",
    "sort",
    "filter",
    "is_show_more",
]


class DisplayHints:
    def __init__(
        self,
        *,
        path: SDPath,
        node_hint: NodeDisplayHint,
        table_hint: TableDisplayHint,
        attributes_hint: AttributesDisplayHint,
    ) -> None:
        # This inventory path is an 'abc' path because it's the general, abstract path of a display
        # hint and may contain "*" (ie. placeholders).
        # Concrete paths (in trees) contain node names which are inserted into these placeholders
        # while calculating node titles.
        self.abc_path = path
        self.node_hint = node_hint
        self.table_hint = table_hint
        self.attributes_hint = attributes_hint

        self.nodes: dict[str, DisplayHints] = {}

    @classmethod
    def root(cls) -> DisplayHints:
        path: SDPath = tuple()
        return DisplayHints(
            path=path,
            node_hint=NodeDisplayHint.from_raw(path, {"title": _l("Inventory Tree")}),
            table_hint=TableDisplayHint.from_raw(path, {}, [], OrderedDict()),
            attributes_hint=AttributesDisplayHint(OrderedDict()),
        )

    def parse(self, raw_hints: Mapping[str, InventoryHintSpec]) -> None:
        for path, related_raw_hints in sorted(
            _get_related_raw_hints(raw_hints).items(), key=lambda t: t[0]
        ):
            if not path:
                continue

            parent = self.get_tree_hints(path[:-1])

            node_or_table_hints = InventoryHintSpec()
            for key in _ALLOWED_KEYS:
                if (value := related_raw_hints.for_table.get(key)) is not None:
                    node_or_table_hints[key] = value
                elif (value := related_raw_hints.for_node.get(key)) is not None:
                    node_or_table_hints[key] = value

            table_keys = _complete_key_order(
                related_raw_hints.for_table.get("keyorder", []),
                set(related_raw_hints.by_column),
            )
            attributes_keys = _complete_key_order(
                related_raw_hints.for_node.get("keyorder", []),
                set(related_raw_hints.by_key),
            )

            parent.nodes.setdefault(
                path[-1],
                DisplayHints(
                    path=path,
                    # Some fields like 'title' or 'keyorder' of legacy display hints are declared
                    # either for
                    # - real nodes, eg. ".hardware.chassis.",
                    # - nodes with attributes, eg. ".hardware.cpu." or
                    # - nodes with a table, eg. ".software.packages:"
                    node_hint=NodeDisplayHint.from_raw(path, node_or_table_hints),
                    table_hint=TableDisplayHint.from_raw(
                        path,
                        node_or_table_hints,
                        table_keys,
                        related_raw_hints.by_column,
                    ),
                    attributes_hint=AttributesDisplayHint(
                        OrderedDict(
                            {
                                key: AttributeDisplayHint.from_raw(
                                    path,
                                    key,
                                    related_raw_hints.by_key.get(key, {}),
                                )
                                for key in attributes_keys
                            }
                        )
                    ),
                ),
            )

    def __iter__(self) -> Iterator[DisplayHints]:
        yield from self.make_inventory_paths_or_hints([])

    def make_inventory_paths_or_hints(self, path: list[str]) -> Iterator[DisplayHints]:
        yield self
        for node_name, node in self.nodes.items():
            yield from node.make_inventory_paths_or_hints(path + [node_name])

    def get_attribute_hint(self, key: str) -> AttributeDisplayHint:
        return self.attributes_hint.by_key.get(
            key, AttributeDisplayHint.from_raw(self.abc_path, key, {})
        )

    def get_column_hint(self, key: str) -> ColumnDisplayHint:
        return self.table_hint.by_column.get(
            key, ColumnDisplayHint.from_raw("", self.abc_path, key, {})
        )

    def get_node_hints(self, name: SDNodeName) -> DisplayHints:
        return self.nodes.get(
            name,
            DisplayHints(
                path=self.abc_path,
                node_hint=NodeDisplayHint.from_raw(self.abc_path, {}),
                table_hint=TableDisplayHint.from_raw(self.abc_path, {}, [], OrderedDict()),
                attributes_hint=AttributesDisplayHint(OrderedDict()),
            ),
        )

    def get_tree_hints(self, path: SDPath) -> DisplayHints:
        node = self
        for node_name in path:
            if node_name in node.nodes:
                node = node.nodes[node_name]
            elif "*" in node.nodes:
                node = node.nodes["*"]
            else:
                return DisplayHints(
                    path=path,
                    node_hint=NodeDisplayHint.from_raw(path, {}),
                    table_hint=TableDisplayHint.from_raw(path, {}, [], OrderedDict()),
                    attributes_hint=AttributesDisplayHint(OrderedDict()),
                )
        return node


DISPLAY_HINTS = DisplayHints.root()
