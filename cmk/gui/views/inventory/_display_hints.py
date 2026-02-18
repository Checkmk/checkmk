#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="unreachable"

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="redundant-expr"

# mypy: disable-error-code="type-arg"

from __future__ import annotations

import abc
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
from cmk.gui.color import Color, parse_color_from_api
from cmk.gui.i18n import _, _l
from cmk.gui.ifaceoper import interface_oper_states, interface_port_types
from cmk.gui.inventory.filters import (
    FilterInvBool,
    FilterInvChoice,
    FilterInvFloat,
    FilterInvFloatChoice,
    FilterInvtableAdminStatus,
    FilterInvtableAgeRange,
    FilterInvtableAvailable,
    FilterInvtableChoice,
    FilterInvtableDualChoice,
    FilterInvtableIntegerRange,
    FilterInvtableInterfaceType,
    FilterInvtableOperStatus,
    FilterInvtableText,
    FilterInvtableTextWithSortKey,
    FilterInvtableTimestampAsAge,
    FilterInvtableVersion,
    FilterInvText,
    FilterInvTextWithSortKey,
)
from cmk.gui.log import logger
from cmk.gui.type_defs import DynamicIconName
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
from cmk.inventory_ui.v1_unstable import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Alignment as AlignmentFromAPI
from cmk.inventory_ui.v1_unstable import AutoPrecision as AutoPrecisionFromAPI
from cmk.inventory_ui.v1_unstable import BackgroundColor as BackgroundColorFromAPI
from cmk.inventory_ui.v1_unstable import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_unstable import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_unstable import DecimalNotation as DecimalNotationFromAPI
from cmk.inventory_ui.v1_unstable import (
    EngineeringScientificNotation as EngineeringScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_unstable import entry_point_prefixes
from cmk.inventory_ui.v1_unstable import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1_unstable import Label as LabelFromAPI
from cmk.inventory_ui.v1_unstable import LabelColor as LabelColorFromAPI
from cmk.inventory_ui.v1_unstable import Node as NodeFromAPI
from cmk.inventory_ui.v1_unstable import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_unstable import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1_unstable import (
    StandardScientificNotation as StandardScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_unstable import StrictPrecision as StrictPrecisionFromAPI
from cmk.inventory_ui.v1_unstable import TextField as TextFieldFromAPI
from cmk.inventory_ui.v1_unstable import TimeNotation as TimeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Title as TitleFromAPI
from cmk.inventory_ui.v1_unstable import Unit as UnitFromAPI

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
        case AlignmentFromAPI.CENTER:
            return "center"
        case AlignmentFromAPI.RIGHT:
            return "right"
        case other:
            assert_never(other)


@dataclass(frozen=True, kw_only=True)
class TDStyles:
    css_class: str
    text_align: str
    background_color: str
    color: str
    prevent_line_break: bool


PaintResultFromAPI = tuple[TDStyles, str | HTML]
PaintFunctionFromAPI = Callable[[float, SDValue], PaintResultFromAPI]


def _wrap_paint_function(paint_function: PaintFunction) -> PaintFunctionFromAPI:
    def _wrap(now: float, value: SDValue) -> PaintResultFromAPI:
        css_class, rendered_value = paint_function(value)
        return (
            TDStyles(
                css_class=css_class,
                text_align="",
                background_color="",
                color="",
                prevent_line_break=css_class == "number",
            ),
            rendered_value,
        )

    return _wrap


def _set_text_color(bg_color: Color) -> Color:
    if bg_color.name.startswith("LIGHT_"):
        return Color.BLACK
    if bg_color.name == "DARK_CYAN":
        return Color.BLACK
    if bg_color.name.startswith("DARK_"):
        return Color.WHITE
    if "RED" in bg_color.name:
        return Color.WHITE
    return Color.BLACK


def _compute_td_styles(
    styles: Iterable[AlignmentFromAPI | BackgroundColorFromAPI | LabelColorFromAPI],
    default_alignment: AlignmentFromAPI,
    *,
    prevent_line_break: bool,
) -> TDStyles:
    alignments = []
    background_colors = []
    text_colors = []
    for style in styles:
        match style:
            case AlignmentFromAPI() as alignment_from_api:
                alignments.append(alignment_from_api)
            case BackgroundColorFromAPI() as bg_color_from_api:
                background_colors.append(parse_color_from_api(bg_color_from_api))
            case LabelColorFromAPI() as label_color_from_api:
                text_colors.append(parse_color_from_api(label_color_from_api))
            case other:
                assert_never(other)
    if text_colors:
        color = text_colors[0].value
    else:
        color = _set_text_color(background_colors[0]).value if background_colors else ""
    return TDStyles(
        css_class="",
        text_align=_parse_alignment_from_api(alignments[0] if alignments else default_alignment),
        background_color=background_colors[0].value if background_colors else "",
        color=color,
        prevent_line_break=prevent_line_break,
    )


class _PaintBool:
    def __init__(self, field_from_api: BoolFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.LEFT

    def __call__(self, now: float, value: SDValue) -> PaintResultFromAPI:
        if not isinstance(value, bool):
            return _wrap_paint_function(inv_paint_generic)(now, value)
        return (
            _compute_td_styles(
                self._field.style(value),
                self.default_alignment,
                prevent_line_break=False,
            ),
            _make_str(self._field.render_true if value else self._field.render_false),
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

    def __call__(self, now: float, value: SDValue) -> PaintResultFromAPI:
        if not isinstance(value, (int | float)):
            return _wrap_paint_function(inv_paint_generic)(now, value)

        match self._field.render:
            case c if callable(c):
                rendered_value = _make_str(c(value))
            case UnitFromAPI() as unit:
                rendered_value = _render_unit(unit, value, now)
            case _:
                assert_never(self._field.render)

        return (
            _compute_td_styles(
                self._field.style(value),
                self.default_alignment,
                prevent_line_break=True,
            ),
            rendered_value,
        )


class _PaintText:
    def __init__(self, field_from_api: TextFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.LEFT

    def __call__(self, now: float, value: SDValue) -> PaintResultFromAPI:
        if not isinstance(value, str):
            return _wrap_paint_function(inv_paint_generic)(now, value)
        return (
            _compute_td_styles(
                self._field.style(value),
                self.default_alignment,
                prevent_line_break=False,
            ),
            _make_str(_make_str(self._field.render(value))),
        )


class _PaintChoice:
    def __init__(self, field_from_api: ChoiceFieldFromAPI) -> None:
        self._field = field_from_api

    @property
    def default_alignment(self) -> AlignmentFromAPI:
        return AlignmentFromAPI.CENTER

    def __call__(self, now: float, value: SDValue) -> PaintResultFromAPI:
        if not isinstance(value, (int | float | str)):
            return _wrap_paint_function(inv_paint_generic)(now, value)
        return (
            _compute_td_styles(
                self._field.style(value),
                self.default_alignment,
                prevent_line_break=False,
            ),
            (
                f"<{value}> (%s)" % _("No such value")
                if (rendered := self._field.mapping.get(value)) is None
                else _make_str(rendered)
            ),
        )


def _make_paint_function(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
) -> PaintFunctionFromAPI:
    match field_from_api:
        case BoolFieldFromAPI():
            return _PaintBool(field_from_api)
        case NumberFieldFromAPI():
            return _PaintNumber(field_from_api)
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


def _get_unit_choices_from_number_field(
    number_field: NumberFieldFromAPI,
) -> Mapping[str, FilterInvFloatChoice]:
    if not isinstance(number_field.render, UnitFromAPI):
        return {}
    match number_field.render.notation:
        case (
            DecimalNotationFromAPI()
            | StandardScientificNotationFromAPI()
            | EngineeringScientificNotationFromAPI()
        ):
            return {}
        case SINotationFromAPI():
            return {
                prefix: FilterInvFloatChoice(
                    f"{prefix}{number_field.render.notation.symbol}", factor
                )
                for prefix, factor in (
                    ("", 1),
                    ("k", 1000),
                    ("M", 1000**2),
                    ("G", 1000**3),
                    ("T", 1000**4),
                    ("P", 1000**5),
                    ("E", 1000**6),
                    ("Z", 1000**7),
                    ("Y", 1000**8),
                )
            }
        case IECNotationFromAPI():
            return {
                prefix: FilterInvFloatChoice(
                    f"{prefix}{number_field.render.notation.symbol}", factor
                )
                for prefix, factor in (
                    ("", 1),
                    ("Ki", 1024),
                    ("Mi", 1024**2),
                    ("Gi", 1024**3),
                    ("Ti", 1024**4),
                    ("Pi", 1024**5),
                    ("Ei", 1024**6),
                    ("Zi", 1024**7),
                    ("Yi", 1024**8),
                )
            }
        case TimeNotationFromAPI() | AgeNotationFromAPI():
            return {
                "": FilterInvFloatChoice("s", 1),
                "min": FilterInvFloatChoice("min", 60),
                "h": FilterInvFloatChoice("h", 3600),
                "d": FilterInvFloatChoice("d", 86400),
            }
        case other:
            raise TypeError(other)


def _make_attribute_filter(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
    *,
    filter_ident: str,
    long_title: str,
    inventory_path: inventory.InventoryPath,
) -> FilterInvFloat | FilterInvText | FilterInvChoice | FilterInvTextWithSortKey:
    match field_from_api:
        case BoolFieldFromAPI():
            return FilterInvChoice(
                ident=filter_ident,
                title=long_title,
                inventory_path=inventory_path,
                options=[
                    ("True", _make_str(field_from_api.render_true)),
                    ("False", _make_str(field_from_api.render_false)),
                ],
                is_show_more=True,
            )
        case NumberFieldFromAPI():
            return FilterInvFloat(
                ident=filter_ident,
                title=long_title,
                inventory_path=inventory_path,
                unit_choices=_get_unit_choices_from_number_field(field_from_api),
            )
        case TextFieldFromAPI():
            if field_from_api.sort_key:
                return FilterInvTextWithSortKey(
                    ident=filter_ident,
                    title=long_title,
                    inventory_path=inventory_path,
                    sort_key=field_from_api.sort_key,
                    is_show_more=True,
                )
            return FilterInvText(
                ident=filter_ident,
                title=long_title,
                inventory_path=inventory_path,
                is_show_more=True,
            )
        case ChoiceFieldFromAPI():
            return FilterInvChoice(
                ident=filter_ident,
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
            filter_ident=name,
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


def _is_choice(len_mapping: int) -> bool:
    return len_mapping <= 10


def _make_column_filter(
    field_from_api: BoolFieldFromAPI | NumberFieldFromAPI | TextFieldFromAPI | ChoiceFieldFromAPI,
    *,
    table_view_name: str,
    filter_ident: str,
    long_title: str,
) -> (
    FilterInvtableAgeRange
    | FilterInvtableChoice
    | FilterInvtableDualChoice
    | FilterInvtableIntegerRange
    | FilterInvtableText
    | FilterInvtableTextWithSortKey
):
    match field_from_api:
        case BoolFieldFromAPI():
            return FilterInvtableChoice(
                inv_info=table_view_name,
                ident=filter_ident,
                title=long_title,
                options=[
                    ("True", _make_str(field_from_api.render_true)),
                    ("False", _make_str(field_from_api.render_false)),
                ],
            )
        case NumberFieldFromAPI():
            if isinstance(field_from_api.render, UnitFromAPI) and isinstance(
                field_from_api.render.notation, AgeNotationFromAPI
            ):
                return FilterInvtableAgeRange(
                    inv_info=table_view_name,
                    ident=filter_ident,
                    title=long_title,
                    unit_choices=_get_unit_choices_from_number_field(field_from_api),
                )
            return FilterInvtableIntegerRange(
                inv_info=table_view_name,
                ident=filter_ident,
                title=long_title,
                unit_choices=_get_unit_choices_from_number_field(field_from_api),
            )
        case TextFieldFromAPI():
            if field_from_api.sort_key:
                return FilterInvtableTextWithSortKey(
                    inv_info=table_view_name,
                    ident=filter_ident,
                    title=long_title,
                    sort_key=field_from_api.sort_key,
                )
            return FilterInvtableText(
                inv_info=table_view_name,
                ident=filter_ident,
                title=long_title,
            )
        case ChoiceFieldFromAPI():
            if _is_choice(len(field_from_api.mapping)):
                return FilterInvtableChoice(
                    inv_info=table_view_name,
                    ident=filter_ident,
                    title=long_title,
                    options=[(k, _make_str(v)) for k, v in field_from_api.mapping.items()],
                )
            return FilterInvtableDualChoice(
                inv_info=table_view_name,
                ident=filter_ident,
                title=long_title,
                choices=[(str(k), _make_str(v)) for k, v in field_from_api.mapping.items()],
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
            field_from_api,
            table_view_name=table_view_name,
            filter_ident=name,
            long_title=long_title,
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
        table = TableWithView(
            columns={
                SDKey(k): _parse_col_field_of_view_from_api(table_view_name, title, k, v)
                for k, v in node.table.columns.items()
            },
            name=table_view_name,
            path=path,
            long_title=_make_long_title(parent_title, _make_str(node.table.view.title)),
            icon=DynamicIconName(""),
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


def _get_unit_choices_from_legacy_data_type(data_type: str) -> Mapping[str, FilterInvFloatChoice]:
    match data_type:
        case "bytes" | "bytes_rounded" | "size":
            return {
                prefix: FilterInvFloatChoice(f"{prefix}B", factor)
                for prefix, factor in (
                    ("", 1),
                    ("k", 1000),
                    ("M", 1000**2),
                    ("G", 1000**3),
                    ("T", 1000**4),
                    ("P", 1000**5),
                    ("E", 1000**6),
                    ("Z", 1000**7),
                    ("Y", 1000**8),
                )
            }
        case "hz":
            return {
                prefix: FilterInvFloatChoice(f"{prefix}Hz", factor)
                for prefix, factor in (
                    ("", 1),
                    ("k", 1000),
                    ("M", 1000**2),
                    ("G", 1000**3),
                    ("T", 1000**4),
                    ("P", 1000**5),
                    ("E", 1000**6),
                    ("Z", 1000**7),
                    ("Y", 1000**8),
                )
            }
        case "volt":
            return {"": FilterInvFloatChoice("V", 1)}
        case "age" | "timestamp_as_age" | "timestamp_as_age_days":
            return {
                "": FilterInvFloatChoice("s", 1),
                "min": FilterInvFloatChoice("min", 60),
                "h": FilterInvFloatChoice("h", 3600),
                "d": FilterInvFloatChoice("d", 86400),
            }
        case "nic_speed":
            return {
                prefix: FilterInvFloatChoice(f"{prefix}bits/s", factor)
                for prefix, factor in (
                    ("", 1),
                    ("k", 1000),
                    ("M", 1000**2),
                    ("G", 1000**3),
                    ("T", 1000**4),
                    ("P", 1000**5),
                    ("E", 1000**6),
                    ("Z", 1000**7),
                    ("Y", 1000**8),
                )
            }
        case _:
            return {}


def _make_attribute_filter_from_legacy_hint(
    *, path: SDPath, key: str, data_type: str, filter_ident: str, title: str, is_show_more: bool
) -> FilterInvText | FilterInvChoice | FilterInvFloat:
    inventory_path = inventory.InventoryPath(
        path=path,
        source=inventory.TreeSource.attributes,
        key=SDKey(key),
    )
    match data_type:
        case "str":
            return FilterInvText(
                ident=filter_ident,
                title=title,
                inventory_path=inventory_path,
                is_show_more=is_show_more,
            )
        case "bool":
            return FilterInvChoice(
                ident=filter_ident,
                title=title,
                inventory_path=inventory_path,
                options=[
                    ("True", _("yes")),
                    ("False", _("no")),
                ],
                is_show_more=True,
            )
        case _:
            return FilterInvFloat(
                ident=filter_ident,
                title=title,
                inventory_path=inventory_path,
                unit_choices=_get_unit_choices_from_legacy_data_type(data_type),
            )


@dataclass(frozen=True, kw_only=True)
class AttributeDisplayHint:
    name: str
    title: str
    short_title: str
    long_title: str
    paint_function: PaintFunctionFromAPI
    sort_function: SortFunction
    filter: FilterInvText | FilterInvFloat | FilterInvChoice | FilterInvTextWithSortKey

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory attribute: %s") % self.long_title


def _parse_attr_field_from_legacy(
    *,
    path: SDPath,
    node_name: str,
    node_title: str,
    key: str,
    legacy_hint: InventoryHintSpec,
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
        paint_function=_wrap_paint_function(paint_function),
        sort_function=_make_sort_function_of_legacy_hint(legacy_hint),
        filter=_make_attribute_filter_from_legacy_hint(
            path=path,
            key=key,
            data_type=data_type,
            filter_ident=name,
            title=long_title,
            is_show_more=legacy_hint.get("is_show_more", True),
        ),
    )


@dataclass(frozen=True, kw_only=True)
class ColumnDisplayHint:
    title: str
    short_title: str
    long_title: str
    paint_function: PaintFunctionFromAPI

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory column: %s") % self.long_title


def _parse_col_field_from_legacy(
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
        paint_function=_wrap_paint_function(paint_function),
    )


def _parse_col_filter_from_legacy(
    *,
    table_view_name: str,
    filter_ident: str,
    title: str,
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
    data_type: str,
) -> (
    FilterInvtableAgeRange
    | FilterInvtableChoice
    | FilterInvtableDualChoice
    | FilterInvtableIntegerRange
    | FilterInvtableText
    | FilterInvtableTextWithSortKey
    | FilterInvtableVersion
):
    if not filter_class:
        if unit_choices := _get_unit_choices_from_legacy_data_type(data_type):
            return FilterInvtableIntegerRange(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                unit_choices=unit_choices,
            )
        return FilterInvtableText(
            inv_info=table_view_name,
            ident=filter_ident,
            title=title,
        )
    match filter_class.__name__:
        case "FilterInvtableAdminStatus":
            return FilterInvtableChoice(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                options=[
                    ("1", _("up")),
                    ("2", _("down")),
                ],
            )
        case "FilterInvtableAvailable":
            return FilterInvtableChoice(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                options=[
                    ("True", _("free")),
                    ("False", _("used")),
                ],
            )
        case "FilterInvtableIntegerRange":
            return FilterInvtableIntegerRange(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                unit_choices=_get_unit_choices_from_legacy_data_type(data_type),
            )
        case "FilterInvtableInterfaceType":
            return FilterInvtableDualChoice(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                choices=[
                    (str(k), str(v))
                    for k, v in sorted(interface_port_types().items(), key=lambda t: t[0])
                ],
            )
        case "FilterInvtableOperStatus":
            return FilterInvtableChoice(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                options=[
                    (str(state), title)
                    for state, title in interface_oper_states().items()
                    # needed because of silly types
                    # skip artificial state 8 (degraded) and 9 (admin down)
                    if isinstance(state, int) and state < 8
                ],
            )
        case "FilterInvtableText":
            return FilterInvtableText(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
            )
        case "FilterInvtableTimestampAsAge":
            return FilterInvtableAgeRange(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
                unit_choices={
                    "": FilterInvFloatChoice("s", 1),
                    "min": FilterInvFloatChoice("min", 60),
                    "h": FilterInvFloatChoice("h", 3600),
                    "d": FilterInvFloatChoice("d", 86400),
                },
            )
        case "FilterInvtableVersion":
            return FilterInvtableVersion(
                inv_info=table_view_name,
                ident=filter_ident,
                title=title,
            )
    raise TypeError(filter_class)


@dataclass(frozen=True, kw_only=True)
class ColumnDisplayHintOfView:
    name: str
    title: str
    short_title: str
    long_title: str
    paint_function: PaintFunctionFromAPI
    sort_function: SortFunction
    filter: (
        FilterInvtableAgeRange
        | FilterInvtableChoice
        | FilterInvtableDualChoice
        | FilterInvtableIntegerRange
        | FilterInvtableText
        | FilterInvtableTextWithSortKey
        | FilterInvtableTimestampAsAge
        | FilterInvtableVersion
    )

    @property
    def long_inventory_title(self) -> str:
        return _("Inventory column: %s") % self.long_title


def _parse_col_field_from_legacy_of_view(
    *,
    table_view_name: str,
    node_title: str,
    key: str,
    legacy_hint: InventoryHintSpec,
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
        paint_function=_wrap_paint_function(paint_function),
        sort_function=_make_sort_function_of_legacy_hint(legacy_hint),
        filter=_parse_col_filter_from_legacy(
            table_view_name=table_view_name,
            filter_ident=name,
            title=long_title,
            filter_class=legacy_hint.get("filter"),
            data_type=legacy_hint.get("paint", ""),
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
    icon: DynamicIconName
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
                paint_function=_wrap_paint_function(
                    inv_paint_funtions["inv_paint_generic"]["func"]
                ),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=_make_attribute_filter_from_legacy_hint(
                    path=self.path,
                    key=key,
                    data_type="str",
                    filter_ident=name,
                    title=long_title,
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
                paint_function=_wrap_paint_function(
                    inv_paint_funtions["inv_paint_generic"]["func"]
                ),
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
        icon = node_or_table_hints.get("icon", DynamicIconName(""))
        table: Table | TableWithView
        if table_view_name := (
            "" if "*" in path else _parse_view_name(node_or_table_hints.get("view", ""))
        ):
            table = TableWithView(
                columns={
                    SDKey(key): _parse_col_field_from_legacy_of_view(
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
                    SDKey(key): _parse_col_field_from_legacy(
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
                SDKey(key): _parse_attr_field_from_legacy(
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


@dataclass(frozen=True, kw_only=True)
class FilterMigration(abc.ABC):
    name: str

    @abc.abstractmethod
    def __call__(self, filter_vars: Mapping[str, str]) -> Mapping[str, str]: ...


@dataclass(frozen=True, kw_only=True)
class FilterMigrationScale(FilterMigration):
    prefix: Literal["M"]

    def __call__(self, filter_vars: Mapping[str, str]) -> Mapping[str, str]:
        migrated = {}
        for direction in ("from", "until"):
            if filter_value := filter_vars.get(f"{self.name}_{direction}"):
                migrated[f"{self.name}_{direction}"] = filter_value
                migrated[f"{self.name}_{direction}_prefix"] = self.prefix
        return migrated


@dataclass(frozen=True, kw_only=True)
class FilterMigrationTime(FilterMigration):
    prefix: Literal["d"]

    def __call__(self, filter_vars: Mapping[str, str]) -> Mapping[str, str]:
        migrated = {}
        for direction in ("from", "until"):
            if (filter_value := filter_vars.get(f"{self.name}_{direction}_days")) is None:
                filter_value = filter_vars.get(f"{self.name}_{direction}")
            if filter_value:
                migrated[f"{self.name}_{direction}"] = filter_value
                migrated[f"{self.name}_{direction}_prefix"] = self.prefix
        return migrated


@dataclass(frozen=True, kw_only=True)
class FilterMigrationChoice(FilterMigration):
    choices: Sequence[int | float | str]

    def __call__(self, filter_vars: Mapping[str, str]) -> Mapping[str, str]:
        # FilterInvtableAdminStatus
        match filter_vars.get(self.name):
            case "1":
                migrated = {f"{self.name}_{c}": "" for c in self.choices}
                migrated[f"{self.name}_1"] = "on"
                return migrated
            case "2":
                migrated = {f"{self.name}_{c}": "" for c in self.choices}
                migrated[f"{self.name}_2"] = "on"
                return migrated
            case "-1":
                # legacy ignore
                return {f"{self.name}_{c}": "on" for c in self.choices}
            case _:
                # FilterInvtableOperStatus
                return {
                    f"{self.name}_{c}": filter_vars.get(f"{self.name}_{c}", "")
                    for c in self.choices
                }


@dataclass(frozen=True, kw_only=True)
class FilterMigrationBool(FilterMigration):
    def __call__(self, filter_vars: Mapping[str, str]) -> Mapping[str, str]:
        # FilterInvtableAvailable
        match filter_vars.get(self.name):
            case "yes":
                return {f"{self.name}_True": "on", f"{self.name}_False": ""}
            case "no":
                return {f"{self.name}_True": "", f"{self.name}_False": "on"}
            case "":
                # legacy ignore
                return {f"{self.name}_{c}": "on" for c in (True, False)}
            case _:
                return {
                    f"{self.name}_{c}": filter_vars.get(f"{self.name}_{c}", "")
                    for c in (True, False)
                }


@dataclass(frozen=True, kw_only=True)
class FilterMigrationBoolIs(FilterMigration):
    def __call__(self, filter_vars: Mapping[str, str]) -> Mapping[str, str]:
        # FilterInvBool
        match filter_vars.get(f"is_{self.name}"):
            case "1":
                return {f"{self.name}_True": "on", f"{self.name}_False": ""}
            case "0":
                return {f"{self.name}_True": "", f"{self.name}_False": "on"}
            case "-1":
                # legacy ignore
                return {f"{self.name}_{c}": "on" for c in (True, False)}
            case _:
                return {
                    f"{self.name}_{c}": filter_vars.get(f"{self.name}_{c}", "")
                    for c in (True, False)
                }


def find_non_canonical_filters(
    plugins: DiscoveredPlugins[NodeFromAPI], legacy_hints: Mapping[str, InventoryHintSpec]
) -> Mapping[str, FilterMigration]:
    filters: dict[str, FilterMigration] = {
        # "bytes"
        "inv_hardware_cpu_cache_size": FilterMigrationScale(
            name="inv_hardware_cpu_cache_size", prefix="M"
        ),
        # "bytes_rounded"
        "inv_hardware_memory_total_ram_usable": FilterMigrationScale(
            name="inv_hardware_memory_total_ram_usable", prefix="M"
        ),
        "inv_hardware_memory_total_swap": FilterMigrationScale(
            name="inv_hardware_memory_total_swap", prefix="M"
        ),
        "inv_hardware_memory_total_vmalloc": FilterMigrationScale(
            name="inv_hardware_memory_total_vmalloc", prefix="M"
        ),
        # "hz"
        "inv_hardware_cpu_bus_speed": FilterMigrationScale(
            name="inv_hardware_cpu_bus_speed", prefix="M"
        ),
        "inv_hardware_cpu_max_speed": FilterMigrationScale(
            name="inv_hardware_cpu_max_speed", prefix="M"
        ),
        #
        "invinterface_last_change": FilterMigrationTime(
            name="invinterface_last_change", prefix="d"
        ),
    }

    for node in sorted(plugins.plugins.values(), key=lambda n: len(n.path)):
        if node.table.view is None:
            continue
        for key, field_from_api in node.table.columns.items():
            name = f"{node.table.view.name}_{key}"
            if (
                isinstance(field_from_api, NumberFieldFromAPI)
                and isinstance(field_from_api.render, UnitFromAPI)
                and isinstance(field_from_api.render.notation, AgeNotationFromAPI)
            ):
                filters.setdefault(name, FilterMigrationTime(name=name, prefix="d"))

            elif isinstance(field_from_api, ChoiceFieldFromAPI) and _is_choice(
                len(field_from_api.mapping)
            ):
                filters.setdefault(
                    name,
                    FilterMigrationChoice(
                        name=name,
                        choices=list(field_from_api.mapping),
                    ),
                )

            elif isinstance(field_from_api, BoolFieldFromAPI):
                filters.setdefault(name, FilterMigrationBool(name=name))

    for raw_path, legacy_hint in legacy_hints.items():
        inv_path = inventory.parse_internal_raw_path(raw_path)
        if not inv_path.key:
            continue
        if inv_path.source == inventory.TreeSource.attributes:
            name = "_".join(["inv"] + [str(e) for e in inv_path.path] + [str(inv_path.key)])
            match legacy_hint.get("paint"):
                case "bytes" | "bytes_rounded":
                    filters[name] = FilterMigrationScale(name=name, prefix="M")
                case "hz":
                    filters[name] = FilterMigrationScale(name=name, prefix="M")
                case "bool":
                    filters.setdefault(name, FilterMigrationBoolIs(name=name))
        if (
            inv_path.source == inventory.TreeSource.table
            and (view_name := legacy_hint.get("view"))
            and (legacy_filter := legacy_hint.get("filter"))
        ):
            name = f"{_parse_view_name(view_name)}_{inv_path.key}"
            match legacy_filter.__class__.__name__:
                case "FilterInvtableOperStatus":
                    filters.setdefault(
                        name,
                        FilterMigrationChoice(
                            name=name,
                            choices=["1", "2", "3", "4", "5", "6", "7"],
                        ),
                    )
                case "FilterInvtableAdminStatus":
                    filters.setdefault(
                        name,
                        FilterMigrationChoice(
                            name=name,
                            choices=["1", "2"],
                        ),
                    )
                case "FilterInvtableAvailable":
                    filters.setdefault(name, FilterMigrationBool(name=name))
                case "FilterInvtableTimestampAsAge":
                    filters.setdefault(name, FilterMigrationTime(name=name, prefix="d"))
    return filters


def register_display_hints(
    plugins: DiscoveredPlugins[NodeFromAPI], legacy_hints: Mapping[str, InventoryHintSpec]
) -> None:
    for hint in _parse_legacy_display_hints(legacy_hints):
        inv_display_hints.add(hint)

    for node in sorted(plugins.plugins.values(), key=lambda n: len(n.path)):
        inv_display_hints.add(_parse_node_from_api(node))
