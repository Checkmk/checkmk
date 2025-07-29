#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import assert_never, Literal, TypeAlias

import cmk.ccc.debug
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.gui import inventory
from cmk.gui.i18n import _, _l
from cmk.gui.inventory.filters import (
    FilterInvBool,
    FilterInvChoice,
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
from cmk.gui.log import logger
from cmk.gui.utils.html import HTML
from cmk.inventory_ui.v1_alpha import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_alpha import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_alpha import entry_point_prefixes
from cmk.inventory_ui.v1_alpha import Label as LabelFromAPI
from cmk.inventory_ui.v1_alpha import Node as NodeFromAPI
from cmk.inventory_ui.v1_alpha import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_alpha import TextField as TextFieldFromAPI
from cmk.inventory_ui.v1_alpha import Title as TitleFromAPI
from cmk.inventory_ui.v1_alpha import Unit as UnitFromAPI
from cmk.utils.structured_data import SDKey, SDNodeName, SDPath

from .registry import (
    inv_paint_funtions,
    InventoryHintSpec,
    InvValue,
    PaintFunction,
    SortFunction,
)

# TODO API: style


def load_inventory_ui_plugins() -> DiscoveredPlugins[NodeFromAPI]:
    discovered_plugins: DiscoveredPlugins[NodeFromAPI] = discover_all_plugins(
        PluginGroup.INVENTORY_UI,
        entry_point_prefixes(),
        raise_errors=cmk.ccc.debug.enabled(),
    )
    for exc in discovered_plugins.errors:
        logger.error(exc)
    return discovered_plugins


def _find_icon(path: SDPath) -> str:
    if path == (SDNodeName("hardware"),):
        return "hardware"
    if path == (SDNodeName("software"),):
        return "software"
    if path == (SDNodeName("software"), SDNodeName("packages")):
        return "packages"
    if path == (SDNodeName("software"), SDNodeName("applications"), SDNodeName("docker")):
        return "docker"
    if path == (SDNodeName("networking"),):
        return "networking"
    return ""


def _make_str(title_or_label: TitleFromAPI | LabelFromAPI | str) -> str:
    return (
        title_or_label.localize(lambda v: v)
        if isinstance(title_or_label, (TitleFromAPI | LabelFromAPI))
        else title_or_label
    )


class _RenderBool:
    def __init__(self, field_from_api: BoolFieldFromAPI) -> None:
        self._field = field_from_api

    def __call__(self, value: int | float | str | bool | None) -> tuple[str, str | HTML]:
        if value is None:
            return "", ""
        if not isinstance(value, bool):
            raise ValueError(value)
        return "", _make_str(self._field.render_true if value else self._field.render_false)


class _RenderChoice:
    def __init__(self, field_from_api: ChoiceFieldFromAPI) -> None:
        self._field = field_from_api

    def __call__(self, value: int | float | str | bool | None) -> tuple[str, str | HTML]:
        if value is None:
            return "", ""
        if not isinstance(value, (int | float | str)):
            raise ValueError(value)
        return (
            "",
            f"{value} (%s)" % _("No such value")
            if (rendered := self._field.mapping.get(value)) is None
            else _make_str(rendered),
        )


def _make_paint_function(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> PaintFunction:
    match field_from_api:
        case BoolFieldFromAPI():
            return _RenderBool(field_from_api)
        case NumberFieldFromAPI():
            return lambda v: ("", str(v))  # TODO
        case TextFieldFromAPI():
            return lambda v: ("", str(v))  # TODO
        case ChoiceFieldFromAPI():
            return _RenderChoice(field_from_api)
        case other:
            assert_never(other)


class _SortFunctionText:
    def __init__(self, text_field: TextFieldFromAPI) -> None:
        self._text_field = text_field

    def __call__(self, val_a: InvValue, val_b: InvValue) -> int:
        if not isinstance(val_a, str):
            raise TypeError(val_a)

        if not isinstance(val_b, str):
            raise TypeError(val_a)

        if self._text_field.sort_key is None:
            return (val_a > val_b) - (val_a < val_b)

        parsed_val_a = self._text_field.sort_key(val_a)
        parsed_val_b = self._text_field.sort_key(val_b)
        return (parsed_val_a > parsed_val_b) - (parsed_val_a < parsed_val_b)


class _SortFunctionChoice:
    def __init__(self, choice_field: ChoiceFieldFromAPI) -> None:
        self._choice_field = choice_field

    def __call__(self, val_a: InvValue, val_b: InvValue) -> int:
        keys = list(self._choice_field.mapping)

        if val_a in keys:
            index_a = keys.index(val_a)
        else:
            return -1 if val_b in keys else 0

        if val_b in keys:
            index_b = keys.index(val_b)
        else:
            return -1 if val_a in keys else 0

        return (index_a > index_b) - (index_a < index_b)


def _make_sort_function(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> SortFunction:
    match field_from_api:
        case BoolFieldFromAPI():
            return _cmp_inv_generic
        case NumberFieldFromAPI():
            return _cmp_inv_generic
        case TextFieldFromAPI():
            return _SortFunctionText(field_from_api)
        case ChoiceFieldFromAPI():
            return _SortFunctionChoice(field_from_api)
        case other:
            assert_never(other)


def _get_unit_from_number_field(number_field: NumberFieldFromAPI) -> str:
    return (
        number_field.render.notation.symbol if isinstance(number_field.render, UnitFromAPI) else ""
    )


def _make_attribute_filter(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
    *,
    name: str,
    long_title: str,
    inventory_path: inventory.InventoryPath,
) -> FilterInvBool | FilterInvFloat | FilterInvText | FilterInvChoice:
    match field_from_api:
        case BoolFieldFromAPI():
            return FilterInvBool(
                ident=name,
                title=long_title,
                inventory_path=inventory_path,
                is_show_more=True,
            )
        case NumberFieldFromAPI():
            # TODO unit/scale?
            return FilterInvFloat(
                ident=name,
                title=long_title,
                inventory_path=inventory_path,
                unit=_get_unit_from_number_field(field_from_api),
                scale=1,
                is_show_more=True,
            )
        case TextFieldFromAPI():
            return FilterInvText(
                ident=name,
                title=long_title,
                inventory_path=inventory_path,
                is_show_more=True,
            )
        case ChoiceFieldFromAPI():
            return FilterInvChoice(
                ident=name,
                title=long_title,
                inventory_path=inventory_path,
                options=[(k, _make_str(v)) for k, v in field_from_api.mapping.items()],
                is_show_more=True,
            )
        case other:
            assert_never(other)


def _parse_attr_field_from_api(
    path: SDPath,
    node_ident: str,
    node_title: str,
    key: str,
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> AttributeDisplayHint:
    name = _make_attr_name(node_ident, key)
    title = _make_str(field_from_api.title)
    long_title = _make_long_title(node_title, title)
    return AttributeDisplayHint(
        name=name,
        title=title,
        short_title=title,
        long_title=long_title,
        paint_function=_make_paint_function(field_from_api),
        sort_function=_decorate_sort_function(_make_sort_function(field_from_api)),
        filter=_make_attribute_filter(
            field_from_api,
            name=name,
            long_title=long_title,
            inventory_path=inventory.InventoryPath(
                path=path,
                source=inventory.TreeSource.attributes,
                key=SDKey(key),
            ),
        ),
    )


def _parse_col_field_from_api(
    node_title: str,
    key: str,
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> ColumnDisplayHint:
    title = _make_str(field_from_api.title)
    return ColumnDisplayHint(
        title=title,
        short_title=title,
        long_title=_make_long_title(node_title, title),
        paint_function=_make_paint_function(field_from_api),
    )


def _parse_col_field_from_api_of_view(
    table_view_name: str,
    node_title: str,
    key: str,
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> ColumnDisplayHintOfView:
    name = _make_col_name(table_view_name, key)
    title = _make_str(field_from_api.title)
    long_title = _make_long_title(node_title, title)
    return ColumnDisplayHintOfView(
        name=name,
        title=title,
        short_title=title,
        long_title=long_title,
        paint_function=_make_paint_function(field_from_api),
        sort_function=_decorate_sort_function(_make_sort_function(field_from_api)),
        filter=FilterInvtableText(  # TODO
            inv_info=table_view_name,
            ident=name,
            title=long_title,
        ),
    )


def _parse_node_from_api(node: NodeFromAPI) -> NodeDisplayHint:
    path = tuple(SDNodeName(e) for e in node.path)
    parent_title = inv_display_hints.get_node_hint(path[:-1]).title if path[:-1] else ""
    name = _make_node_name(path)
    title = _make_str(node.title)
    table: Table | TableWithView
    if node.table.view is None:
        table = Table(
            columns={
                SDKey(k): _parse_col_field_from_api(title, k, v)
                for k, v in node.table.columns.items()
            },
        )
    else:
        table_view_name = _parse_view_name(node.table.view.name)
        long_title = _make_long_title(parent_title, _make_str(node.table.view.title))
        if node.table.view.group is not None:
            # TODO CMK-25037
            long_title = f"{long_title} (_make_str(node.table.view.group))"
        table = TableWithView(
            columns={
                SDKey(k): _parse_col_field_from_api_of_view(table_view_name, title, k, v)
                for k, v in node.table.columns.items()
            },
            name=table_view_name,
            path=path,
            long_title=long_title,
            icon="",
            is_show_more=True,
        )
    return NodeDisplayHint(
        name=name,
        path=path,
        title=title,
        short_title=title,
        long_title=_make_long_title(parent_title, title),
        icon=_find_icon(path),
        attributes={
            SDKey(k): _parse_attr_field_from_api(path, name, title, k, v)
            for k, v in node.attributes.items()
        },
        table=table,
    )


@dataclass(frozen=True)
class _RelatedLegacyHints:
    for_node: InventoryHintSpec = field(default_factory=lambda: InventoryHintSpec())
    for_table: InventoryHintSpec = field(default_factory=lambda: InventoryHintSpec())
    by_column: dict[str, InventoryHintSpec] = field(default_factory=dict)
    by_key: dict[str, InventoryHintSpec] = field(default_factory=dict)


def _get_related_legacy_hints(
    legacy_hints: Mapping[str, InventoryHintSpec],
) -> Mapping[SDPath, _RelatedLegacyHints]:
    related_legacy_hints_by_path: dict[SDPath, _RelatedLegacyHints] = {}
    for raw_path, legacy_hint in legacy_hints.items():
        inventory_path = inventory.parse_internal_raw_path(raw_path)
        related_legacy_hints = related_legacy_hints_by_path.setdefault(
            inventory_path.path,
            _RelatedLegacyHints(),
        )

        if inventory_path.source == inventory.TreeSource.node:
            related_legacy_hints.for_node.update(legacy_hint)
            continue

        if inventory_path.source == inventory.TreeSource.table:
            if inventory_path.key:
                related_legacy_hints.by_column.setdefault(inventory_path.key, legacy_hint)
                continue

            related_legacy_hints.for_table.update(legacy_hint)
            continue

        if inventory_path.source == inventory.TreeSource.attributes and inventory_path.key:
            related_legacy_hints.by_key.setdefault(inventory_path.key, legacy_hint)
            continue

    return related_legacy_hints_by_path


PAINT_FUNCTION_NAME_PREFIX = "inv_paint_"


def _get_paint_function(legacy_hint: InventoryHintSpec) -> tuple[str, PaintFunction]:
    # FIXME At the moment  we need it to get tdclass: Clean this up one day.
    if "paint" in legacy_hint:
        data_type = legacy_hint["paint"]
        return data_type, inv_paint_funtions[PAINT_FUNCTION_NAME_PREFIX + data_type]["func"]
    return "str", inv_paint_funtions["inv_paint_generic"]["func"]


def _make_sort_function_of_legacy_hint(legacy_hint: InventoryHintSpec) -> SortFunction:
    return _decorate_sort_function(legacy_hint.get("sort", _cmp_inv_generic))


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


def _make_title_function(legacy_hint: InventoryHintSpec) -> Callable[[str], str]:
    if "title" not in legacy_hint:
        return lambda word: word.replace("_", " ").title()

    if callable(title := legacy_hint["title"]):
        # TODO Do we still need this?
        return title

    return lambda word: str(title)


def _make_long_title(parent_title: str, title: str) -> str:
    return parent_title + " ➤ " + title if parent_title else title


def _make_node_name(path: SDPath) -> str:
    return "_".join(["inv"] + list(path))


def _make_attr_name(node_name: str, key: SDKey | str) -> str:
    return f"{node_name}_{key}"


def _make_col_name(table_view_name: str, key: SDKey | str) -> str:
    return f"{table_view_name}_{key}" if table_view_name else ""


def _make_attribute_filter_from_legacy_hint(
    *, path: SDPath, key: str, data_type: str, name: str, long_title: str, is_show_more: bool
) -> FilterInvText | FilterInvBool | FilterInvFloat:
    inventory_path = inventory.InventoryPath(
        path=path,
        source=inventory.TreeSource.attributes,
        key=SDKey(key),
    )
    match data_type:
        case "str":
            return FilterInvText(
                ident=name,
                title=long_title,
                inventory_path=inventory_path,
                is_show_more=is_show_more,
            )
        case "bool":
            return FilterInvBool(
                ident=name,
                title=long_title,
                inventory_path=inventory_path,
                is_show_more=is_show_more,
            )
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
        ident=name,
        title=long_title,
        inventory_path=inventory_path,
        unit=unit,
        scale=scale,
        is_show_more=is_show_more,
    )


@dataclass(frozen=True, kw_only=True)
class AttributeDisplayHint:
    name: str
    title: str
    short_title: str
    long_title: str
    paint_function: PaintFunction
    sort_function: SortFunction
    filter: FilterInvText | FilterInvBool | FilterInvFloat | FilterInvChoice

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory attribute: %s") % self.long_title


def _parse_attribute_hint(
    *, path: SDPath, node_name: str, node_title: str, key: str, legacy_hint: InventoryHintSpec
) -> AttributeDisplayHint:
    data_type, paint_function = _get_paint_function(legacy_hint)
    name = _make_attr_name(node_name, key)
    title = _make_title_function(legacy_hint)(key)
    long_title = _make_long_title(node_title, title)
    return AttributeDisplayHint(
        name=name,
        title=title,
        short_title=(
            title if (short_title := legacy_hint.get("short")) is None else str(short_title)
        ),
        long_title=long_title,
        paint_function=paint_function,
        sort_function=_make_sort_function_of_legacy_hint(legacy_hint),
        filter=_make_attribute_filter_from_legacy_hint(
            path=path,
            key=key,
            data_type=data_type,
            name=name,
            long_title=long_title,
            is_show_more=legacy_hint.get("is_show_more", True),
        ),
    )


@dataclass(frozen=True, kw_only=True)
class ColumnDisplayHint:
    title: str
    short_title: str
    long_title: str
    paint_function: PaintFunction

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory column: %s") % self.long_title


def _parse_column_hint(
    *, node_title: str, key: str, legacy_hint: InventoryHintSpec
) -> ColumnDisplayHint:
    _data_type, paint_function = _get_paint_function(legacy_hint)
    title = _make_title_function(legacy_hint)(key)
    return ColumnDisplayHint(
        title=title,
        short_title=(
            title if (short_title := legacy_hint.get("short")) is None else str(short_title)
        ),
        long_title=_make_long_title(node_title, title),
        paint_function=paint_function,
    )


def _parse_column_display_hint_filter_class(
    table_view_name: str,
    name: str,
    long_title: str,
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
    FilterInvtableAdminStatus
    | FilterInvtableAvailable
    | FilterInvtableIntegerRange
    | FilterInvtableInterfaceType
    | FilterInvtableOperStatus
    | FilterInvtableText
    | FilterInvtableTimestampAsAge
    | FilterInvtableVersion
):
    if not filter_class:
        return FilterInvtableText(
            inv_info=table_view_name,
            ident=name,
            title=long_title,
        )
    match filter_class.__name__:
        case "FilterInvtableAdminStatus":
            return FilterInvtableAdminStatus(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableAvailable":
            return FilterInvtableAvailable(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableIntegerRange":
            return FilterInvtableIntegerRange(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableInterfaceType":
            return FilterInvtableInterfaceType(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableOperStatus":
            return FilterInvtableOperStatus(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableText":
            return FilterInvtableText(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableTimestampAsAge":
            return FilterInvtableTimestampAsAge(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case "FilterInvtableVersion":
            return FilterInvtableVersion(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
    raise TypeError(filter_class)


@dataclass(frozen=True, kw_only=True)
class ColumnDisplayHintOfView:
    name: str
    title: str
    short_title: str
    long_title: str
    paint_function: PaintFunction
    sort_function: SortFunction
    filter: (
        FilterInvtableAdminStatus
        | FilterInvtableAvailable
        | FilterInvtableIntegerRange
        | FilterInvtableInterfaceType
        | FilterInvtableOperStatus
        | FilterInvtableText
        | FilterInvtableTimestampAsAge
        | FilterInvtableVersion
    )

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory column: %s") % self.long_title


def _parse_column_hint_of_view(
    *, table_view_name: str, node_title: str, key: str, legacy_hint: InventoryHintSpec
) -> ColumnDisplayHintOfView:
    _data_type, paint_function = _get_paint_function(legacy_hint)
    name = _make_col_name(table_view_name, key)
    title = _make_title_function(legacy_hint)(key)
    long_title = _make_long_title(node_title, title)
    return ColumnDisplayHintOfView(
        name=name,
        title=title,
        short_title=(
            title if (short_title := legacy_hint.get("short")) is None else str(short_title)
        ),
        long_title=long_title,
        paint_function=paint_function,
        sort_function=_make_sort_function_of_legacy_hint(legacy_hint),
        filter=_parse_column_display_hint_filter_class(
            table_view_name, name, long_title, legacy_hint.get("filter")
        ),
    )


def _parse_view_name(view_name: str) -> str:
    if not view_name:
        return ""
    if not view_name.startswith("inv"):
        view_name = f"inv{view_name}"
    if view_name.endswith("_of_host"):
        view_name = view_name[:-8]
    return view_name


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


OrderedAttributeDisplayHints: TypeAlias = Mapping[SDKey, AttributeDisplayHint]
OrderedColumnDisplayHints: TypeAlias = Mapping[SDKey, ColumnDisplayHint]


@dataclass(frozen=True, kw_only=True)
class Table:
    columns: OrderedColumnDisplayHints


OrderedColumnDisplayHintsOfView: TypeAlias = Mapping[SDKey, ColumnDisplayHintOfView]


@dataclass(frozen=True, kw_only=True)
class TableWithView:
    columns: OrderedColumnDisplayHintsOfView
    name: str
    path: SDPath
    long_title: str
    icon: str
    is_show_more: bool

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory table: %s") % self.long_title


@dataclass(frozen=True, kw_only=True)
class NodeDisplayHint:
    name: str
    path: SDPath
    title: str
    short_title: str
    long_title: str
    icon: str
    attributes: OrderedAttributeDisplayHints
    table: Table | TableWithView

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory node: %s") % self.long_title

    def get_attribute_hint(self, key: str) -> AttributeDisplayHint:
        def _default() -> AttributeDisplayHint:
            name = _make_attr_name(self.name, key)
            title = key.replace("_", " ").title()
            long_title = _make_long_title(self.title if self.path else "", title)
            return AttributeDisplayHint(
                name=name,
                title=title,
                short_title=title,
                long_title=long_title,
                paint_function=inv_paint_funtions["inv_paint_generic"]["func"],
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=_make_attribute_filter_from_legacy_hint(
                    path=self.path,
                    key=key,
                    data_type="str",
                    name=name,
                    long_title=long_title,
                    is_show_more=True,
                ),
            )

        return hint if (hint := self.attributes.get(SDKey(key))) else _default()

    def get_column_hint(self, key: str) -> ColumnDisplayHint | ColumnDisplayHintOfView:
        def _default() -> ColumnDisplayHint:
            title = key.replace("_", " ").title()
            return ColumnDisplayHint(
                title=title,
                short_title=title,
                long_title=_make_long_title(self.title if self.path else "", title),
                paint_function=inv_paint_funtions["inv_paint_generic"]["func"],
            )

        return hint if (hint := self.table.columns.get(SDKey(key))) else _default()


def _parse_legacy_display_hints(
    legacy_hints: Mapping[str, InventoryHintSpec],
) -> Iterator[NodeDisplayHint]:
    for path, related_legacy_hints in sorted(
        _get_related_legacy_hints(legacy_hints).items(), key=lambda t: len(t[0])
    ):
        if not path:
            continue

        node_or_table_hints = InventoryHintSpec()
        for key in _ALLOWED_KEYS:
            if (value := related_legacy_hints.for_table.get(key)) is not None:
                node_or_table_hints[key] = value
            elif (value := related_legacy_hints.for_node.get(key)) is not None:
                node_or_table_hints[key] = value

        # Some fields like 'title' or 'keyorder' of legacy display hints are declared
        # either for
        # - real nodes, eg. ".hardware.chassis.",
        # - nodes with attributes, eg. ".hardware.cpu." or
        # - nodes with a table, eg. ".software.packages:"
        name = _make_node_name(path)
        title = _make_title_function(node_or_table_hints)(path[-1] if path else "")
        long_title = _make_long_title(
            inv_display_hints.get_node_hint(path[:-1]).title if path[:-1] else "",
            title,
        )
        icon = node_or_table_hints.get("icon", "")
        table: Table | TableWithView
        if table_view_name := (
            "" if "*" in path else _parse_view_name(node_or_table_hints.get("view", ""))
        ):
            table = TableWithView(
                columns={
                    SDKey(key): _parse_column_hint_of_view(
                        table_view_name=table_view_name,
                        node_title=title,
                        key=key,
                        legacy_hint=related_legacy_hints.by_column.get(key, {}),
                    )
                    for key in _complete_key_order(
                        related_legacy_hints.for_table.get("keyorder", []),
                        set(related_legacy_hints.by_column),
                    )
                },
                name=table_view_name,
                path=path,
                long_title=long_title,
                icon=icon,
                is_show_more=node_or_table_hints.get("is_show_more", True),
            )
        else:
            table = Table(
                columns={
                    SDKey(key): _parse_column_hint(
                        node_title=title,
                        key=key,
                        legacy_hint=related_legacy_hints.by_column.get(key, {}),
                    )
                    for key in _complete_key_order(
                        related_legacy_hints.for_table.get("keyorder", []),
                        set(related_legacy_hints.by_column),
                    )
                }
            )
        yield NodeDisplayHint(
            name=name,
            path=path,
            title=title,
            short_title=title,
            long_title=long_title,
            icon=icon,
            attributes={
                SDKey(key): _parse_attribute_hint(
                    path=path,
                    node_name=name,
                    node_title=title,
                    key=key,
                    legacy_hint=related_legacy_hints.by_key.get(key, {}),
                )
                for key in _complete_key_order(
                    related_legacy_hints.for_node.get("keyorder", []),
                    set(related_legacy_hints.by_key),
                )
            },
            table=table,
        )


class DisplayHints:
    def __init__(self) -> None:
        self._nodes_by_path: dict[SDPath, NodeDisplayHint] = {
            (): NodeDisplayHint(
                name=_make_node_name(()),
                path=(),
                title=str(_l("Inventory tree")),
                short_title=str(_l("Inventory tree")),
                long_title=str(_l("Inventory tree")),
                icon="",
                attributes={},
                table=Table(columns={}),
            )
        }

    def add(self, node_hint: NodeDisplayHint) -> None:
        if node_hint.path in self._nodes_by_path:
            return
        self._nodes_by_path[node_hint.path] = node_hint

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
            if all(right in (left, "*") for left, right in zip(path, abc_path)):
                return abc_path
        return None

    def get_node_hint(self, path: SDPath) -> NodeDisplayHint:
        if not path:
            return self._nodes_by_path[()]
        if (abc_path := self._find_abc_path(path)) in self._nodes_by_path:
            return self._nodes_by_path[abc_path]
        title = path[-1].replace("_", " ").title()
        return NodeDisplayHint(
            name=_make_node_name(path),
            path=path,
            title=title,
            short_title=title,
            long_title=_make_long_title(
                self.get_node_hint(path[:-1]).title if path[:-1] else "",
                title,
            ),
            icon="",
            attributes={},
            table=Table(columns={}),
        )


inv_display_hints = DisplayHints()


def register_display_hints(
    plugins: DiscoveredPlugins[NodeFromAPI], legacy_hints: Mapping[str, InventoryHintSpec]
) -> None:
    for node in sorted(plugins.plugins.values(), key=lambda n: len(n.path)):
        inv_display_hints.add(_parse_node_from_api(node))

    for hint in _parse_legacy_display_hints(legacy_hints):
        inv_display_hints.add(hint)
