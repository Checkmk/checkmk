#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from cmk.utils.structured_data import SDKey, SDPath

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


def _make_long_title(parent_title: str, title: str) -> str:
    return parent_title + " ➤ " + title if parent_title else title


def _make_ident(path: SDPath, key: str = "") -> str:
    parts = ["inv"] + list(path)
    if key:
        parts.append(key)
    return "_".join(parts)


@dataclass(frozen=True)
class AttributeDisplayHint:
    path: SDPath
    key: SDKey
    title: str
    short_title: str
    long_title: str
    data_type: str
    paint_function: PaintFunction
    sort_function: SortFunction
    is_show_more: bool

    @property
    def ident(self) -> str:
        return _make_ident(self.path, self.key)

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory attribute: %s") % self.long_title

    @classmethod
    def from_raw(
        cls,
        parent_title: str,
        path: SDPath,
        key: str,
        raw_hint: InventoryHintSpec,
    ) -> AttributeDisplayHint:
        data_type, paint_function = _get_paint_function(raw_hint)
        title = _make_title_function(raw_hint)(key)
        return cls(
            path=path,
            key=SDKey(key),
            title=title,
            short_title=(
                title if (short_title := raw_hint.get("short")) is None else str(short_title)
            ),
            long_title=_make_long_title(parent_title, title),
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
    path: SDPath
    title: str
    by_key: OrderedDict[str, AttributeDisplayHint]

    def get_attribute_hint(self, key: str) -> AttributeDisplayHint:
        return (
            hint
            if (hint := self.by_key.get(key))
            else AttributeDisplayHint.from_raw(self.title if self.path else "", self.path, key, {})
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
    long_title: str
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
    def long_inventory_title(self) -> str:
        return _("Inventory column: %s") % self.long_title

    @classmethod
    def from_raw(
        cls,
        parent_title: str,
        view_name: str,
        path: SDPath,
        key: str,
        raw_hint: InventoryHintSpec,
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
            long_title=_make_long_title(parent_title, title),
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
    path: SDPath
    title: str
    long_title: str
    icon: str
    is_show_more: bool
    view_name: str
    by_column: OrderedDict[str, ColumnDisplayHint]

    @classmethod
    def from_raw(
        cls,
        parent_title: str,
        path: SDPath,
        raw_hint: InventoryHintSpec,
        key_order: Sequence[str],
        by_column: Mapping[str, InventoryHintSpec],
    ) -> TableDisplayHint:
        title = _make_title_function(raw_hint)(path[-1]) if path else ""
        view_name = "" if "*" in path else _parse_view_name(raw_hint.get("view"))
        return cls(
            path=path,
            title=title,
            long_title=_make_long_title(parent_title, title),
            icon=raw_hint.get("icon", ""),
            is_show_more=raw_hint.get("is_show_more", True),
            # See DYNAMIC-PATHS
            view_name=view_name,
            by_column=OrderedDict(
                {
                    key: ColumnDisplayHint.from_raw(
                        title,
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
    def long_inventory_title(self) -> str:
        return _("Inventory table: %s") % self.long_title

    def get_column_hint(self, key: str) -> ColumnDisplayHint:
        return (
            hint
            if (hint := self.by_column.get(key))
            else ColumnDisplayHint.from_raw(self.title, "", self.path, key, {})
        )


@dataclass(frozen=True)
class NodeDisplayHint:
    path: SDPath
    title: str
    short_title: str
    long_title: str
    icon: str
    attributes_hint: AttributesDisplayHint
    table_hint: TableDisplayHint

    @property
    def ident(self) -> str:
        return _make_ident(self.path)

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory node: %s") % self.long_title

    @classmethod
    def from_raw(
        cls,
        parent_title: str,
        path: SDPath,
        raw_hint: InventoryHintSpec,
        attributes_key_order: Sequence[str],
        attributes_by_key: Mapping[str, InventoryHintSpec],
        table_key_order: Sequence[str],
        table_by_column: Mapping[str, InventoryHintSpec],
    ) -> NodeDisplayHint:
        title = _make_title_function(raw_hint)(path[-1] if path else "")
        return cls(
            path=path,
            title=title,
            short_title=title,
            long_title=_make_long_title(parent_title, title),
            icon=raw_hint.get("icon", ""),
            attributes_hint=AttributesDisplayHint(
                path,
                title,
                OrderedDict(
                    {
                        key: AttributeDisplayHint.from_raw(
                            title,
                            path,
                            key,
                            attributes_by_key.get(key, {}),
                        )
                        for key in _complete_key_order(attributes_key_order, set(attributes_by_key))
                    }
                ),
            ),
            table_hint=TableDisplayHint.from_raw(
                parent_title,
                path,
                raw_hint,
                _complete_key_order(table_key_order, set(table_by_column)),
                table_by_column,
            ),
        )


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


@dataclass(frozen=True)
class DisplayHints:
    _nodes_by_path: dict[SDPath, NodeDisplayHint] = field(default_factory=dict)

    def add(self, node_hint: NodeDisplayHint) -> None:
        self._nodes_by_path[node_hint.path] = node_hint

    @classmethod
    def root(cls) -> DisplayHints:
        hints = cls()
        hints.add(
            NodeDisplayHint.from_raw(
                "",
                (),
                {"title": _l("Inventory Tree")},
                [],
                {},
                [],
                {},
            )
        )
        return hints

    def parse(self, raw_hints: Mapping[str, InventoryHintSpec]) -> None:
        for path, related_raw_hints in sorted(
            _get_related_raw_hints(raw_hints).items(), key=lambda t: t[0]
        ):
            if not path:
                continue

            node_or_table_hints = InventoryHintSpec()
            for key in _ALLOWED_KEYS:
                if (value := related_raw_hints.for_table.get(key)) is not None:
                    node_or_table_hints[key] = value
                elif (value := related_raw_hints.for_node.get(key)) is not None:
                    node_or_table_hints[key] = value

            # Some fields like 'title' or 'keyorder' of legacy display hints are declared
            # either for
            # - real nodes, eg. ".hardware.chassis.",
            # - nodes with attributes, eg. ".hardware.cpu." or
            # - nodes with a table, eg. ".software.packages:"
            self.add(
                NodeDisplayHint.from_raw(
                    self.get_node_hint(path[:-1]).title if path[:-1] else "",
                    path,
                    node_or_table_hints,
                    related_raw_hints.for_node.get("keyorder", []),
                    related_raw_hints.by_key,
                    related_raw_hints.for_table.get("keyorder", []),
                    related_raw_hints.by_column,
                )
            )

    def __iter__(self) -> Iterator[NodeDisplayHint]:
        yield from self._nodes_by_path.values()

    def _find_abc_path(self, path: SDPath) -> SDPath | None:
        # This inventory path is an 'abc' path because it's the general, abstract path of a display
        # hint and may contain "*" (ie. placeholders).
        # Concrete paths (in trees) contain node names which are inserted into these placeholders
        # while calculating node titles.
        for abc_path in self._nodes_by_path:
            if len(path) != len(abc_path):
                continue
            if all(r in (l, "*") for l, r in zip(path, abc_path)):
                return abc_path
        return None

    def get_node_hint(self, path: SDPath) -> NodeDisplayHint:
        if not path:
            return self._nodes_by_path[()]
        if (abc_path := self._find_abc_path(path)) in self._nodes_by_path:
            return self._nodes_by_path[abc_path]
        return NodeDisplayHint.from_raw(
            self.get_node_hint(path[:-1]).title if path[:-1] else "",
            path,
            {},
            [],
            {},
            [],
            {},
        )


DISPLAY_HINTS = DisplayHints.root()
