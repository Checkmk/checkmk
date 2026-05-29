#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

import datetime
from collections.abc import Callable

import pytest

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.inventory._tree import InventoryPath, TreeSource
from cmk.gui.inventory.filters import (
    FilterInvText,
)
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    _PaintBool,
    _PaintChoice,
    _PaintNumber,
    _PaintText,
    _parse_view_name,
    _SortFunctionChoice,
    _SortFunctionText,
    _wrap_paint_function,
    AttributeDisplayHint,
    ColumnDisplayHint,
    DisplayHints,
    inv_display_hints,
    NodeDisplayHint,
    Table,
    TableWithView,
    TDStyles,
)
from cmk.gui.views.inventory._paint_functions import (
    inv_paint_generic,
)
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.inventory.structured_data import SDKey, SDNodeName, SDPath
from cmk.inventory_ui.v1_unstable import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Alignment as AlignmentFromAPI
from cmk.inventory_ui.v1_unstable import BackgroundColor as BackgroundColorFromAPI
from cmk.inventory_ui.v1_unstable import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_unstable import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_unstable import DecimalNotation as DecimalNotationFromAPI
from cmk.inventory_ui.v1_unstable import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1_unstable import Label as LabelFromAPI
from cmk.inventory_ui.v1_unstable import LabelColor as LabelColorFromAPI
from cmk.inventory_ui.v1_unstable import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_unstable import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1_unstable import (
    StandardScientificNotation as StandardScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_unstable import TextField as TextFieldFromAPI
from cmk.inventory_ui.v1_unstable import TimeNotation as TimeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Title as TitleFromAPI
from cmk.inventory_ui.v1_unstable import Unit as UnitFromAPI


def test_display_hint_titles() -> None:
    assert not inventory_displayhints


@pytest.mark.parametrize(
    "val_a, val_b, result",
    [
        (None, None, 0),
        (None, 0, -1),
        (0, None, 1),
        (0, 0, 0),
        (1, 0, 1),
        (0, 1, -1),
    ],
)
def test__cmp_inv_generic(val_a: object, val_b: object, result: int) -> None:
    assert _decorate_sort_function(_cmp_inv_generic)(val_a, val_b) == result


@pytest.mark.parametrize(
    "path, expected_node_hint",
    [
        (
            (),
            NodeDisplayHint(
                name="inv",
                path=(),
                icon="",
                title="Inventory tree",
                short_title="Inventory tree",
                long_title="Inventory tree",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                name="inv_path_to_node",
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                icon="",
                title="Node",
                short_title="Node",
                long_title="To ➤ Node",
                attributes={},
                table=Table(columns={}),
            ),
        ),
    ],
)
def test_make_node_displayhint(path: SDPath, expected_node_hint: NodeDisplayHint) -> None:
    node_hint = inv_display_hints.get_node_hint(path)

    assert node_hint.name == expected_node_hint.name
    assert node_hint.icon == expected_node_hint.icon
    assert node_hint.title == expected_node_hint.title
    assert node_hint.long_title == expected_node_hint.long_title
    assert node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(node_hint.attributes) == list(expected_node_hint.attributes)
    assert list(node_hint.table.columns) == list(expected_node_hint.table.columns)

    if isinstance(expected_node_hint.table, TableWithView):
        assert isinstance(node_hint.table, TableWithView)
        assert node_hint.table.name == expected_node_hint.table.name
        assert node_hint.table.path == expected_node_hint.table.path
        assert node_hint.table.long_title == expected_node_hint.table.long_title
        assert node_hint.table.icon == expected_node_hint.table.icon
        assert node_hint.table.is_show_more == expected_node_hint.table.is_show_more


def test_get_node_hint_returns_registered_hint_verbatim() -> None:
    """Cover the "registered hint is returned faithfully" branch of
    DisplayHints.get_node_hint without depending on a production
    inv-UI plug-in registering anything."""
    hints = DisplayHints()
    registered = NodeDisplayHint(
        name="inv_hardware",
        path=(SDNodeName("hardware"),),
        icon="hardware",
        title="Hardware",
        short_title="Hardware",
        long_title="Hardware",
        attributes={},
        table=Table(columns={}),
    )
    hints.add(registered)

    node_hint = hints.get_node_hint((SDNodeName("hardware"),))

    assert node_hint.name == "inv_hardware"
    assert node_hint.icon == "hardware"
    assert node_hint.title == "Hardware"
    assert node_hint.short_title == "Hardware"
    assert node_hint.long_title == "Hardware"
    assert list(node_hint.attributes) == []
    assert list(node_hint.table.columns) == []


@pytest.mark.parametrize(
    "raw_path, expected_node_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                name="invfoo_bar",
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                name="invfoo_bar",
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                attributes={},
                table=Table(columns={}),
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_path: str, expected_node_hint: NodeDisplayHint
) -> None:
    node_hint = inv_display_hints.get_node_hint(
        cmk.gui.inventory.parse_internal_raw_path(raw_path).path
    )

    assert node_hint.name == "_".join(("inv",) + node_hint.path)
    assert node_hint.icon == expected_node_hint.icon
    assert node_hint.title == expected_node_hint.title
    assert node_hint.long_title == expected_node_hint.long_title
    assert node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(node_hint.attributes) == list(expected_node_hint.attributes)
    assert list(node_hint.table.columns) == list(expected_node_hint.table.columns)

    if isinstance(expected_node_hint.table, TableWithView):
        assert isinstance(node_hint.table, TableWithView)
        assert node_hint.table.name == expected_node_hint.table.name
        assert node_hint.table.path == expected_node_hint.table.path
        assert node_hint.table.long_title == expected_node_hint.table.long_title
        assert node_hint.table.icon == expected_node_hint.table.icon
        assert node_hint.table.is_show_more == expected_node_hint.table.is_show_more


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            (),
            "key",
            ColumnDisplayHint(
                title="Key",
                short_title="Key",
                long_title="Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                title="Key",
                short_title="Key",
                long_title="Node ➤ Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = inv_display_hints.get_node_hint(path).get_column_hint(key)
    assert isinstance(hint, ColumnDisplayHint)
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                paint_function=_wrap_paint_function(inv_paint_generic),
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(raw_path: str, expected: ColumnDisplayHint) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_column_hint(
        inventory_path.key or ""
    )
    assert isinstance(hint, ColumnDisplayHint)
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            (),
            "key",
            AttributeDisplayHint(
                name="inv_key",
                title="Key",
                short_title="Key",
                long_title="Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_key",
                    title="Key",
                    inventory_path=InventoryPath(
                        path=(),
                        source=TreeSource.attributes,
                        key=SDKey("key"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                name="inv_path_to_node_key",
                title="Key",
                short_title="Key",
                long_title="Node ➤ Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_path_to_node_key",
                    title="Node ➤ Key",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                        source=TreeSource.attributes,
                        key=SDKey("key"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = inv_display_hints.get_node_hint(path).get_attribute_hint(key)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                name="inv_foo_bar",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_foo_bar",
                    title="Foo ➤ Bar",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("foo"),),
                        source=TreeSource.attributes,
                        key=SDKey("bar"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                name="inv_hardware_system_product",
                title="Product",
                short_title="Product",
                long_title="System ➤ Product",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_system_product",
                    title="System ➤ Product",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("system")),
                        source=TreeSource.attributes,
                        key=SDKey("product"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_path: str, expected: AttributeDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_attribute_hint(
        inventory_path.key or ""
    )
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "view_name, expected_view_name",
    [
        ("", ""),
        ("viewname", "invviewname"),
        ("invviewname", "invviewname"),
        ("viewname_of_host", "invviewname"),
        ("invviewname_of_host", "invviewname"),
    ],
)
def test__parse_view_name(view_name: str, expected_view_name: str) -> None:
    assert _parse_view_name(view_name) == expected_view_name


def test_render_bool() -> None:
    bool_field = BoolFieldFromAPI(
        TitleFromAPI("A title"),
        render_true=LabelFromAPI("It's true"),
        render_false=LabelFromAPI("It's false"),
    )
    assert _PaintBool(bool_field)(123, True) == (
        TDStyles(
            css_class="",
            text_align="left",
            background_color="",
            color="",
            prevent_line_break=False,
        ),
        "It's true",
    )
    assert _PaintBool(bool_field)(456, False) == (
        TDStyles(
            css_class="",
            text_align="left",
            background_color="",
            color="",
            prevent_line_break=False,
        ),
        "It's false",
    )


@pytest.mark.parametrize(
    ["render", "value", "expected"],
    [
        pytest.param(lambda v: "one" if v == 1 else "more", 1, "one", id="Callable"),
        pytest.param(
            UnitFromAPI(notation=DecimalNotationFromAPI("count")),
            1.00,
            "1 count",
            id="DecimalNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=SINotationFromAPI("B")),
            1000,
            "1 kB",
            id="SINotation",
        ),
        pytest.param(
            UnitFromAPI(notation=IECNotationFromAPI("bits")),
            1024,
            "1 Kibits",
            id="IECNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=StandardScientificNotationFromAPI("snakes")),
            1000,
            "1e+3 snakes",
            id="StandardScientificNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=TimeNotationFromAPI()),
            60,
            "1 min",
            id="TimeNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=AgeNotationFromAPI()),
            datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC).timestamp(),
            "1 min",
            id="AgeNotation",
        ),
    ],
)
def test_render_number(
    render: Callable[[int | float], LabelFromAPI | str] | UnitFromAPI,
    value: int | float,
    expected: str,
) -> None:
    number_field = NumberFieldFromAPI(
        TitleFromAPI("A title"), render=render, style=lambda _: [AlignmentFromAPI.CENTER]
    )
    now = datetime.datetime(2025, 1, 1, 0, 1, 0, tzinfo=datetime.UTC).timestamp()
    assert _PaintNumber(number_field)(now, value) == (
        TDStyles(
            css_class="",
            text_align="center",
            background_color="",
            color="",
            prevent_line_break=True,
        ),
        expected,
    )


def test_render_text() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [LabelColorFromAPI.PINK],
    )
    assert _PaintText(text_field)(123, "world") == (
        TDStyles(
            css_class="",
            text_align="left",
            background_color="",
            color="#ec48b6",
            prevent_line_break=False,
        ),
        "hello world",
    )


def test_render_text_with_background_color() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [BackgroundColorFromAPI.BLUE],
    )
    assert _PaintText(text_field)(123, "world") == (
        TDStyles(
            css_class="",
            text_align="left",
            background_color="#28a2f3",
            color="#1e262e",
            prevent_line_break=False,
        ),
        "hello world",
    )


def test_render_text_with_background_and_text_color() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [LabelColorFromAPI.PINK, BackgroundColorFromAPI.BLUE],
    )
    assert _PaintText(text_field)(123, "world") == (
        TDStyles(
            css_class="",
            text_align="left",
            background_color="#28a2f3",
            color="#ec48b6",
            prevent_line_break=False,
        ),
        "hello world",
    )


def test_render_choice() -> None:
    choice_field = ChoiceFieldFromAPI(
        TitleFromAPI("A title"),
        mapping={1: LabelFromAPI("One")},
    )
    assert _PaintChoice(choice_field)(123, 1) == (
        TDStyles(
            css_class="",
            text_align="center",
            background_color="",
            color="",
            prevent_line_break=False,
        ),
        "One",
    )
    assert _PaintChoice(choice_field)(456, 2) == (
        TDStyles(
            css_class="",
            text_align="center",
            background_color="",
            color="",
            prevent_line_break=False,
        ),
        "<2> (No such value)",
    )


def test_sort_text() -> None:
    text_field = TextFieldFromAPI(TitleFromAPI("A title"), sort_key=int)
    assert _decorate_sort_function(_SortFunctionText(text_field))("1", "2") == -1
    assert _decorate_sort_function(_SortFunctionText(text_field))("2", "1") == 1


def test_sort_choice() -> None:
    choice_field = ChoiceFieldFromAPI(
        TitleFromAPI("A title"),
        mapping={
            2: LabelFromAPI("Two"),
            1: LabelFromAPI("One"),
        },
    )
    assert _decorate_sort_function(_SortFunctionChoice(choice_field))(1, 2) == 1
    assert _decorate_sort_function(_SortFunctionChoice(choice_field))(2, 1) == -1
