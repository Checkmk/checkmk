#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import time
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from dataclasses import dataclass, field
from typing import assert_never, Literal, TypeAlias

import cmk.ccc.debug
from cmk.discover_plugins import discover_all_plugins, DiscoveredPlugins, PluginGroup
from cmk.gui import inventory
from cmk.gui.color import parse_color_from_api
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _, _l
from cmk.gui.inventory.filters import (
    FilterInvBool,
    FilterInvChoice,
    FilterInvFloat,
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableChoice,
    FilterInvtableDualChoice,
    FilterInvtableIntegerRange,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableText,
    FilterInvtableTimestampAsAge,
    FilterInvtableVersion,
    FilterInvText,
)
from cmk.gui.log import logger
from cmk.gui.unit_formatter import AutoPrecision as AutoPrecisionFormatter
from cmk.gui.unit_formatter import (
    DecimalFormatter,
    EngineeringScientificFormatter,
    IECFormatter,
    SIFormatter,
    StandardScientificFormatter,
    TimeFormatter,
)
from cmk.gui.unit_formatter import StrictPrecision as StrictPrecisionFormatter
from cmk.gui.utils.html import HTML
from cmk.inventory.structured_data import SDKey, SDNodeName, SDPath, SDValue
from cmk.inventory_ui.v1_alpha import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_alpha import Alignment as AlignmentFromAPI
from cmk.inventory_ui.v1_alpha import AutoPrecision as AutoPrecisionFromAPI
from cmk.inventory_ui.v1_alpha import BackgroundColor as BackgroundColorFromAPI
from cmk.inventory_ui.v1_alpha import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_alpha import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_alpha import DecimalNotation as DecimalNotationFromAPI
from cmk.inventory_ui.v1_alpha import (
    EngineeringScientificNotation as EngineeringScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_alpha import entry_point_prefixes
from cmk.inventory_ui.v1_alpha import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1_alpha import Label as LabelFromAPI
from cmk.inventory_ui.v1_alpha import LabelColor as LabelColorFromAPI
from cmk.inventory_ui.v1_alpha import Node as NodeFromAPI
from cmk.inventory_ui.v1_alpha import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_alpha import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1_alpha import (
    StandardScientificNotation as StandardScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_alpha import StrictPrecision as StrictPrecisionFromAPI
from cmk.inventory_ui.v1_alpha import TextField as TextFieldFromAPI
from cmk.inventory_ui.v1_alpha import TimeNotation as TimeNotationFromAPI
from cmk.inventory_ui.v1_alpha import Title as TitleFromAPI
from cmk.inventory_ui.v1_alpha import Unit as UnitFromAPI

from ._paint_functions import inv_paint_generic
from .registry import (
    inv_paint_funtions,
    InventoryHintSpec,
    InvValue,
    PaintFunction,
    SortFunction,
)


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


def _parse_alignment_from_api(alignment: AlignmentFromAPI) -> Literal["left", "center", "right"]:
    match alignment:
        case AlignmentFromAPI.LEFT:
            return "left"
        case AlignmentFromAPI.CENTERED:
            return "center"
        case AlignmentFromAPI.RIGHT:
            return "right"
        case other:
            assert_never(other)


def _add_html_styling(
    rendered_value: str,
    styles: Iterable[AlignmentFromAPI | BackgroundColorFromAPI | LabelColorFromAPI],
    default_alignment: AlignmentFromAPI,
) -> HTML:
    alignment: dict[str, str] = {}
    colors: dict[str, str] = {}
    for style in styles:
        match style:
            case AlignmentFromAPI() as alignment_from_api:
                alignment.setdefault("text-align", _parse_alignment_from_api(alignment_from_api))
            case BackgroundColorFromAPI() as bg_color_from_api:
                colors.setdefault("background-color", parse_color_from_api(bg_color_from_api))
            case LabelColorFromAPI() as label_color_from_api:
                colors.setdefault("color", parse_color_from_api(label_color_from_api))
            case other:
                assert_never(other)
    alignment.setdefault("text-align", _parse_alignment_from_api(default_alignment))
    return HTMLWriter.render_div(
        HTMLWriter.render_span(
            rendered_value,
            style="; ".join(f"{k}: {v}" for k, v in colors.items()),
        ),
        style=f"text-align: {alignment['text-align']}",
    )


class _PaintBool:
    def __init__(self, field_from_api: BoolFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.LEFT

    def __call__(self, value: SDValue) -> tuple[str, str | HTML]:
        if not isinstance(value, bool):
            # TODO CMK-25119
            return inv_paint_generic(value)

        rendered_value = _make_str(self._field.render_true if value else self._field.render_false)
        return "", _add_html_styling(
            rendered_value,
            self._field.style(value),
            default_alignment=self.default_alignment,
        )


def _render_unit(unit: UnitFromAPI, value: int | float, now: float) -> str:
    precision: AutoPrecisionFormatter | StrictPrecisionFormatter
    match unit.precision:
        case AutoPrecisionFromAPI():
            precision = AutoPrecisionFormatter(digits=unit.precision.digits)
        case StrictPrecisionFromAPI():
            precision = StrictPrecisionFormatter(digits=unit.precision.digits)
        case _:
            assert_never(unit.precision)

    match unit.notation:
        case DecimalNotationFromAPI():
            return DecimalFormatter(symbol=unit.notation.symbol, precision=precision).render(value)
        case SINotationFromAPI():
            return SIFormatter(symbol=unit.notation.symbol, precision=precision).render(value)
        case IECNotationFromAPI():
            return IECFormatter(symbol=unit.notation.symbol, precision=precision).render(value)
        case StandardScientificNotationFromAPI():
            return StandardScientificFormatter(
                symbol=unit.notation.symbol, precision=precision
            ).render(value)
        case EngineeringScientificNotationFromAPI():
            return EngineeringScientificFormatter(
                symbol=unit.notation.symbol, precision=precision
            ).render(value)
        case TimeNotationFromAPI():
            return TimeFormatter(symbol=unit.notation.symbol, precision=precision).render(value)
        case AgeNotationFromAPI():
            return TimeFormatter(symbol=unit.notation.symbol, precision=precision).render(
                now - value
            )
        case _:
            assert_never(unit.notation)


class _PaintNumber:
    def __init__(self, field_from_api: NumberFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.RIGHT

    def __call__(self, value: SDValue, now: float) -> tuple[str, str | HTML]:
        if not isinstance(value, (int | float)):
            # TODO CMK-25119
            return inv_paint_generic(value)

        match self._field.render:
            case c if callable(c):
                rendered_value = _make_str(c(value))
            case UnitFromAPI() as unit:
                rendered_value = _render_unit(unit, value, now)
            case _:
                assert_never(self._field.render)

        return "", _add_html_styling(
            rendered_value,
            self._field.style(value),
            default_alignment=self.default_alignment,
        )


class _PaintText:
    def __init__(self, field_from_api: TextFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.LEFT

    def __call__(self, value: SDValue) -> tuple[str, str | HTML]:
        if not isinstance(value, str):
            # TODO CMK-25119
            return inv_paint_generic(value)

        return "", _add_html_styling(
            _make_str(_make_str(self._field.render(value))),
            self._field.style(value),
            default_alignment=self.default_alignment,
        )


class _PaintChoice:
    def __init__(self, field_from_api: ChoiceFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.CENTERED

    def __call__(self, value: SDValue) -> tuple[str, str | HTML]:
        if not isinstance(value, (int | float | str)):
            # TODO CMK-25119
            return inv_paint_generic(value)

        rendered_val = (
            f"<{value}> (%s)" % _("No such value")
            if (rendered := self._field.mapping.get(value)) is None
            else _make_str(rendered)
        )
        return "", _add_html_styling(
            rendered_val,
            self._field.style(value),
            default_alignment=self.default_alignment,
        )


def _make_paint_function(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> PaintFunction:
    match field_from_api:
        case BoolFieldFromAPI():
            return _PaintBool(field_from_api)
        case NumberFieldFromAPI():
            return lambda value: _PaintNumber(field_from_api)(value, time.time())
        case TextFieldFromAPI():
            return _PaintText(field_from_api)
        case ChoiceFieldFromAPI():
            return _PaintChoice(field_from_api)
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
    non_canonical_filters: Mapping[str, int],
) -> AttributeDisplayHint:
    name = _make_attr_name(node_ident, key, non_canonical_filters)
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


def _make_column_filter(
    key: str,
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
    *,
    table_view_name: str,
    name: str,
    long_title: str,
) -> (
    FilterInvtableText
    | FilterInvtableIntegerRange
    | FilterInvtableChoice
    | FilterInvtableDualChoice
):
    match field_from_api:
        case BoolFieldFromAPI():
            return FilterInvtableChoice(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
                options=[
                    ("True", _make_str(field_from_api.render_true)),
                    ("False", _make_str(field_from_api.render_false)),
                    ("None", "None"),
                ],
            )
        case NumberFieldFromAPI():
            # TODO unit/scale?
            return FilterInvtableIntegerRange(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
                unit=_get_unit_from_number_field(field_from_api),
                scale=1,
            )
        case TextFieldFromAPI():
            return FilterInvtableText(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
            )
        case ChoiceFieldFromAPI():
            if len(field_from_api.mapping) <= 10:
                return FilterInvtableChoice(
                    inv_info=table_view_name,
                    ident=name,
                    title=long_title,
                    options=[(k, _make_str(v)) for k, v in field_from_api.mapping.items()],
                )
            return FilterInvtableDualChoice(
                inv_info=table_view_name,
                ident=name,
                title=long_title,
                options=[(k, _make_str(v)) for k, v in field_from_api.mapping.items()],
            )
        case other:
            assert_never(other)


def _parse_col_field_of_view_from_api(
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
        filter=_make_column_filter(
            key,
            field_from_api,
            table_view_name=table_view_name,
            name=name,
            long_title=long_title,
        ),
    )


def _parse_node_from_api(
    node: NodeFromAPI, non_canonical_filters: Mapping[str, int]
) -> NodeDisplayHint:
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
                SDKey(k): _parse_col_field_of_view_from_api(table_view_name, title, k, v)
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
            SDKey(k): _parse_attr_field_from_api(path, name, title, k, v, non_canonical_filters)
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


def _make_attr_name(
    node_name: str, key: SDKey | str, non_canonical_filters: Mapping[str, int]
) -> str:
    return f"{name}_canonical" if (name := f"{node_name}_{key}") in non_canonical_filters else name


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
            unit = _("B")
        case "hz":
            unit = _("Hz")
        case "volt":
            unit = _("V")
        case "timestamp":
            unit = _("s")
        case _:
            unit = ""

    return FilterInvFloat(
        ident=name,
        title=long_title,
        inventory_path=inventory_path,
        unit=unit,
        scale=1,
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
    *,
    path: SDPath,
    node_name: str,
    node_title: str,
    key: str,
    legacy_hint: InventoryHintSpec,
    non_canonical_filters: Mapping[str, int],
) -> AttributeDisplayHint:
    data_type, paint_function = _get_paint_function(legacy_hint)
    name = _make_attr_name(node_name, key, non_canonical_filters)
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
                unit="",
                scale=1,
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
        | FilterInvtableChoice
        | FilterInvtableDualChoice
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
            name = _make_attr_name(self.name, key, {})
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
    non_canonical_filters: Mapping[str, int],
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
                    non_canonical_filters=non_canonical_filters,
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


def find_non_canonical_filters(legacy_hints: Mapping[str, InventoryHintSpec]) -> Mapping[str, int]:
    filters = {
        # "bytes"
        "inv_hardware_cpu_cache_size": 1024 * 1024,
        # "bytes_rounded"
        "inv_hardware_memory_total_ram_usable": 1024 * 1024,
        "inv_hardware_memory_total_swap": 1024 * 1024,
        "inv_hardware_memory_total_vmalloc": 1024 * 1024,
        # "hz"
        "inv_hardware_cpu_bus_speed": 1000 * 1000,
        "inv_hardware_cpu_max_speed": 1000 * 1000,
    }
    for raw_path, legacy_hint in legacy_hints.items():
        inv_path = inventory.parse_internal_raw_path(raw_path)
        if inv_path.source != inventory.TreeSource.attributes or not inv_path.key:
            continue
        name = "_".join(["inv"] + [str(e) for e in inv_path.path] + [str(inv_path.key)])
        match legacy_hint.get("paint"):
            case "bytes" | "bytes_rounded":
                filters[name] = 1024 * 1024
            case "hz":
                filters[name] = 1000 * 1000
    return filters


def register_display_hints(
    plugins: DiscoveredPlugins[NodeFromAPI], legacy_hints: Mapping[str, InventoryHintSpec]
) -> None:
    non_canonical_filters = find_non_canonical_filters(legacy_hints)

    for node in sorted(plugins.plugins.values(), key=lambda n: len(n.path)):
        inv_display_hints.add(_parse_node_from_api(node, non_canonical_filters))

    for hint in _parse_legacy_display_hints(legacy_hints, non_canonical_filters):
        inv_display_hints.add(hint)
