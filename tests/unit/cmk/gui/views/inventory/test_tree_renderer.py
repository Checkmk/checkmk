#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

import cmk.utils.render
from cmk.gui.inventory.filters import FilterInvText
from cmk.gui.views.inventory import NodeDisplayHint
from cmk.gui.views.inventory._display_hints import (
    _PaintFunctionAdapter,
    _PaintNumber,
    AttributeDisplayHint,
    ColumnDisplayHint,
    PaintFunctionFromAPI,
    Table,
)
from cmk.gui.views.inventory._paint_functions import (
    inv_paint_age,
    inv_paint_bytes,
    inv_paint_date,
    inv_paint_date_and_time,
    inv_paint_generic,
    inv_paint_volt,
)
from cmk.gui.views.inventory._tree_renderer import (
    _paint_value,
    _PaintValueAndRawValue,
    _replace_title_placeholders,
    _SDDeltaItem,
    _SDDeltaItemsSorter,
    _SDItemsSorter,
    SDItem,
)
from cmk.gui.views.inventory.registry import PaintFunction
from cmk.inventory.delta import ImmutableDeltaAttributes, ImmutableDeltaTable, SDDeltaValue
from cmk.inventory.raw_paths import InventoryPath, TreeSource
from cmk.inventory.trees import (
    ImmutableAttributes,
    ImmutableTable,
    RetentionInterval,
    SDKey,
    SDPath,
    SDValue,
)
from cmk.inventory_ui.v1 import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1 import DecimalNotation as DecimalNotationFromAPI
from cmk.inventory_ui.v1 import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1 import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1 import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1 import StrictPrecision as StrictPrecisionFromAPI
from cmk.inventory_ui.v1 import Title as TitleFromAPI
from cmk.inventory_ui.v1 import Unit as UnitFromAPI


@pytest.mark.parametrize(
    "table, expected",
    [
        (ImmutableTable(), []),
        (
            ImmutableTable(
                key_columns=[SDKey("sid")],
                rows_by_ident={
                    ("SID 2",): {
                        SDKey("sid"): "SID 2",
                        SDKey("flashback"): "Flashback 2",
                        SDKey("other"): "Other 2",
                    },
                    ("SID 1",): {
                        SDKey("sid"): "SID 1",
                        SDKey("flashback"): "Flashback 1",
                        SDKey("other"): "Other 1",
                    },
                    (None,): {
                        SDKey("sid"): None,
                        SDKey("flashback"): None,
                        SDKey("other"): None,
                    },
                },
                retentions={
                    ("SID 2",): {SDKey("sid"): RetentionInterval(1, 2, 3, "previous")},
                },
            ),
            [
                [
                    SDItem(
                        key=SDKey("sid"),
                        title="SID",
                        value="SID 1",
                        retention_interval=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        value="Flashback 1",
                        retention_interval=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key=SDKey("other"),
                        title="Other",
                        value="Other 1",
                        retention_interval=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                        icon_path_svc_problems="",
                    ),
                ],
                [
                    SDItem(
                        key=SDKey("sid"),
                        title="SID",
                        value="SID 2",
                        retention_interval=RetentionInterval(1, 2, 3, "previous"),
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        value="Flashback 2",
                        retention_interval=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key=SDKey("other"),
                        title="Other",
                        value="Other 2",
                        retention_interval=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                        icon_path_svc_problems="",
                    ),
                ],
            ],
        ),
    ],
)
def test_sort_table_rows_displayhint(
    table: ImmutableTable,
    expected: Sequence[Sequence[SDItem]],
) -> None:
    items_sorter = _SDItemsSorter(
        NodeDisplayHint(
            name="inv",
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={},
            table=Table(
                columns={
                    SDKey("sid"): ColumnDisplayHint(
                        title="SID",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("changed"): ColumnDisplayHint(
                        title="Changed",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("foo"): ColumnDisplayHint(
                        title="Foo",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("flashback"): ColumnDisplayHint(
                        title="Flashback",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("other"): ColumnDisplayHint(
                        title="Other",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                }
            ),
        ),
        _paint_value,
        "",
        ImmutableAttributes(),
        table,
    )
    sorted_rows = items_sorter.sort_rows()[-1]
    assert len(sorted_rows) == len(expected)
    for sorted_row, expected_row in zip(sorted_rows, expected):
        assert len(sorted_row) == len(expected_row)
        for item, expected_item in zip(sorted_row, expected_row):
            assert item.key == expected_item.key
            assert item.title == expected_item.title
            assert item.value == expected_item.value
            assert item.retention_interval == expected_item.retention_interval
            assert item.icon_path_svc_problems == expected_item.icon_path_svc_problems


@pytest.mark.parametrize(
    "delta_table, expected",
    [
        (ImmutableDeltaTable(), []),
        (
            ImmutableDeltaTable(
                key_columns=[SDKey("sid")],
                rows=[
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 1", new="SID 1"),
                        SDKey("flashback"): SDDeltaValue(old=None, new=None),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 2", new="SID 2"),
                        SDKey("flashback"): SDDeltaValue(old="Flashback", new="Flashback"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 2", new="SID 2"),
                        SDKey("flashback"): SDDeltaValue(old=None, new=None),
                    },
                ],
            ),
            [],
        ),
        (
            ImmutableDeltaTable(
                key_columns=[SDKey("sid")],
                rows=[
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 1", new="SID 1"),
                        SDKey("flashback"): SDDeltaValue(old=None, new=None),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 2", new="SID 2"),
                        SDKey("flashback"): SDDeltaValue(old="Flashback 21", new="Flashback 22"),
                    },
                ],
            ),
            [
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 2",
                        new="SID 2",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old="Flashback 21",
                        new="Flashback 22",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                ],
            ],
        ),
        (
            ImmutableDeltaTable(
                key_columns=[SDKey("sid")],
                rows=[
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 2", new=None),
                        SDKey("flashback"): SDDeltaValue(old=None, new="Flashback 2"),
                        SDKey("other"): SDDeltaValue(old="Other 2", new="Other 2"),
                        SDKey("changed"): SDDeltaValue(old="Changed 21", new="Changed 22"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 1", new=None),
                        SDKey("flashback"): SDDeltaValue(old=None, new="Flashback 1"),
                        SDKey("other"): SDDeltaValue(old="Other 1", new="Other 1"),
                        SDKey("changed"): SDDeltaValue(old="Changed 11", new="Changed 12"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 3", new="SID 3"),
                        SDKey("flashback"): SDDeltaValue(old="Flashback 3", new="Flashback 3"),
                        SDKey("other"): SDDeltaValue(old=None, new=None),
                        SDKey("changed"): SDDeltaValue(old=None, new=None),
                    },
                ],
            ),
            [
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 1",
                        new=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 11",
                        new="Changed 12",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 1",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 1",
                        new="Other 1",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                ],
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 2",
                        new=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 21",
                        new="Changed 22",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 2",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 2",
                        new="Other 2",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                ],
            ],
        ),
        (
            ImmutableDeltaTable(
                key_columns=[SDKey("sid")],
                rows=[
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 2", new=None),
                        SDKey("flashback"): SDDeltaValue(old=None, new="Flashback 2"),
                        SDKey("other"): SDDeltaValue(old="Other 2", new="Other 2"),
                        SDKey("changed"): SDDeltaValue(old="Changed 21", new="Changed 22"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 1", new=None),
                        SDKey("flashback"): SDDeltaValue(old=None, new="Flashback 1"),
                        SDKey("other"): SDDeltaValue(old="Other 1", new="Other 1"),
                        SDKey("changed"): SDDeltaValue(old="Changed 11", new="Changed 12"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue(old="SID 3", new="SID 3"),
                        SDKey("flashback"): SDDeltaValue(old="Flashback 3", new="Flashback 3"),
                        SDKey("other"): SDDeltaValue(old=None, new=None),
                        SDKey("changed"): SDDeltaValue(old=None, new=None),
                    },
                ],
            ),
            [
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 1",
                        new=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 11",
                        new="Changed 12",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 1",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 1",
                        new="Other 1",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                ],
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 2",
                        new=None,
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 21",
                        new="Changed 22",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 2",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 2",
                        new="Other 2",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                ],
            ],
        ),
    ],
)
def test_sort_delta_table_rows_displayhint(
    delta_table: ImmutableDeltaTable,
    expected: Sequence[Sequence[_SDDeltaItem]],
) -> None:
    delta_items_sorter = _SDDeltaItemsSorter(
        NodeDisplayHint(
            name="inv",
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={},
            table=Table(
                columns={
                    SDKey("sid"): ColumnDisplayHint(
                        title="SID",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("changed"): ColumnDisplayHint(
                        title="Changed",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("foo"): ColumnDisplayHint(
                        title="Foo",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("flashback"): ColumnDisplayHint(
                        title="Flashback",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                    SDKey("other"): ColumnDisplayHint(
                        title="Other",
                        short_title="",
                        long_title="",
                        paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    ),
                }
            ),
        ),
        _paint_value,
        ImmutableDeltaAttributes(),
        delta_table,
    )
    sorted_rows = delta_items_sorter.sort_rows()[-1]
    assert len(sorted_rows) == len(expected)
    for sorted_row, expected_row in zip(sorted_rows, expected):
        assert len(sorted_row) == len(expected_row)
        for item, expected_item in zip(sorted_row, expected_row):
            assert item.key == expected_item.key
            assert item.title == expected_item.title
            assert item.old == expected_item.old
            assert item.new == expected_item.new


@pytest.mark.parametrize(
    "attributes, expected",
    [
        (ImmutableAttributes(), []),
        (
            ImmutableAttributes(
                pairs={
                    SDKey("b"): "B",
                    SDKey("d"): "D",
                    SDKey("c"): "C",
                    SDKey("a"): "A",
                },
                retentions={SDKey("c"): RetentionInterval(1, 2, 3, "previous")},
            ),
            [
                SDItem(
                    key=SDKey("a"),
                    title="A",
                    value="A",
                    retention_interval=None,
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    icon_path_svc_problems="",
                ),
                SDItem(
                    key=SDKey("b"),
                    title="B",
                    value="B",
                    retention_interval=None,
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    icon_path_svc_problems="",
                ),
                SDItem(
                    key=SDKey("d"),
                    title="D",
                    value="D",
                    retention_interval=None,
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    icon_path_svc_problems="",
                ),
                SDItem(
                    key=SDKey("c"),
                    title="C",
                    value="C",
                    retention_interval=RetentionInterval(1, 2, 3, "previous"),
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    icon_path_svc_problems="",
                ),
            ],
        ),
    ],
)
def test_sort_attributes_pairs_displayhint(
    attributes: ImmutableAttributes,
    expected: Sequence[SDItem],
) -> None:
    items_sorter = _SDItemsSorter(
        NodeDisplayHint(
            name="inv",
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={
                SDKey("a"): AttributeDisplayHint(
                    name="inv_a",
                    title="A",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_a",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("a"),
                        ),
                        is_show_more=True,
                    ),
                ),
                SDKey("b"): AttributeDisplayHint(
                    name="inv_b",
                    title="B",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_b",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("b"),
                        ),
                        is_show_more=True,
                    ),
                ),
                SDKey("d"): AttributeDisplayHint(
                    name="inv_d",
                    title="D",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_d",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("d"),
                        ),
                        is_show_more=True,
                    ),
                ),
                SDKey("c"): AttributeDisplayHint(
                    name="inv_c",
                    title="C",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_c",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("c"),
                        ),
                        is_show_more=True,
                    ),
                ),
            },
            table=Table(columns={}),
        ),
        _paint_value,
        "",
        attributes,
        ImmutableTable(),
    )
    sorted_pairs = items_sorter.sort_pairs()
    assert len(sorted_pairs) == len(expected)
    for item, expected_item in zip(sorted_pairs, expected):
        assert item.key == expected_item.key
        assert item.title == expected_item.title
        assert item.value == expected_item.value
        assert item.retention_interval == expected_item.retention_interval
        assert item.icon_path_svc_problems == expected_item.icon_path_svc_problems


@pytest.mark.parametrize(
    "delta_attributes, expected",
    [
        (ImmutableDeltaAttributes(), []),
        (
            ImmutableDeltaAttributes(
                pairs={
                    SDKey("b"): SDDeltaValue(old="B", new=None),
                    SDKey("d"): SDDeltaValue(old=None, new="D"),
                    SDKey("c"): SDDeltaValue(old="C", new="C"),
                    SDKey("a"): SDDeltaValue(old="A1", new="A2"),
                }
            ),
            [
                _SDDeltaItem(
                    key=SDKey("a"),
                    title="A",
                    old="A1",
                    new="A2",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                ),
                _SDDeltaItem(
                    key=SDKey("b"),
                    title="B",
                    old="B",
                    new=None,
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                ),
                _SDDeltaItem(
                    key=SDKey("d"),
                    title="D",
                    old=None,
                    new="D",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                ),
            ],
        ),
    ],
)
def test_sort_delta_attributes_pairs_displayhint(
    delta_attributes: ImmutableDeltaAttributes,
    expected: Sequence[_SDDeltaItem],
) -> None:
    delta_items_sorter = _SDDeltaItemsSorter(
        NodeDisplayHint(
            name="inv",
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={
                SDKey("a"): AttributeDisplayHint(
                    name="inv_a",
                    title="A",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_a",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("a"),
                        ),
                        is_show_more=True,
                    ),
                ),
                SDKey("b"): AttributeDisplayHint(
                    name="inv_c",
                    title="B",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_b",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("b"),
                        ),
                        is_show_more=True,
                    ),
                ),
                SDKey("d"): AttributeDisplayHint(
                    name="inv_d",
                    title="D",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_d",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("d"),
                        ),
                        is_show_more=True,
                    ),
                ),
                SDKey("c"): AttributeDisplayHint(
                    name="inv_c",
                    title="C",
                    short_title="",
                    long_title="",
                    paint_function=_PaintFunctionAdapter(inv_paint_generic),
                    sort_function=lambda *args: 0,  # noqa: ARG005
                    filter=FilterInvText(
                        ident="inv_c",
                        title="",
                        inventory_path=InventoryPath(
                            path=(),
                            source=TreeSource.attributes,
                            key=SDKey("c"),
                        ),
                        is_show_more=True,
                    ),
                ),
            },
            table=Table(columns={}),
        ),
        _paint_value,
        delta_attributes,
        ImmutableDeltaTable(),
    )
    sorted_pairs = delta_items_sorter.sort_pairs()
    assert len(sorted_pairs) == len(expected)
    for item, expected_item in zip(sorted_pairs, expected):
        assert item.key == expected_item.key
        assert item.title == expected_item.title
        assert item.old == expected_item.old
        assert item.new == expected_item.new


@pytest.mark.parametrize(
    "title, abc_path, path, expected_title",
    [
        (
            "Datacenter %d",
            ("software", "applications", "vmwareesx", "*"),
            ("software", "applications", "vmwareesx", "1"),
            "Datacenter 1",
        ),
        (
            "Cluster %d",
            ("software", "applications", "vmwareesx", "*", "clusters", "*"),
            ("software", "applications", "vmwareesx", "1", "clusters", "2"),
            "Cluster 2",
        ),
    ],
)
def test__replace_title_placeholders(
    title: str, abc_path: SDPath, path: SDPath, expected_title: str
) -> None:
    assert (
        _replace_title_placeholders(
            NodeDisplayHint(
                name="",
                path=abc_path,
                icon="",
                title=title,
                short_title=title,
                long_title=title,
                attributes={},
                table=Table(columns={}),
            ),
            path,
        )
        == expected_title
    )


def test_td_spec_tooltip_names_the_validity() -> None:
    item = SDItem(
        key=SDKey("key"),
        title="Title",
        value="value",
        retention_interval=RetentionInterval(100, 20, 3, "previous"),
        paint_function=_PaintFunctionAdapter(inv_paint_generic),
        icon_path_svc_problems="",
    )
    assert cmk.utils.render.date_and_time(120) in str(item.compute_td_spec(121).html_values[0])


_EMPTY_NODE_HINT = NodeDisplayHint(
    name="inv",
    path=(),
    icon="",
    title="",
    short_title="",
    long_title="",
    attributes={},
    table=Table(columns={}),
)


def _painted_attributes(pairs: Mapping[SDKey, SDValue]) -> Sequence[str]:
    return [
        str(item.compute_td_spec(0).html_values[0])
        for item in _SDItemsSorter(
            _EMPTY_NODE_HINT,
            _PaintValueAndRawValue,
            "",
            ImmutableAttributes(pairs=pairs),
            ImmutableTable(),
        ).sort_pairs()
    ]


def test_raw_values_follow_the_painted_values() -> None:
    assert _painted_attributes({SDKey("enabled"): True, SDKey("ratio"): 1.5}) == [
        'Yes <span class="muted_text">(True)</span>',
        '1.50 <span class="muted_text">(1.5)</span>',
    ]


def test_raw_value_is_left_out_if_nothing_is_painted() -> None:
    assert _painted_attributes({SDKey("empty"): ""}) == [""]


def test_raw_values_follow_both_sides_of_a_change() -> None:
    assert [
        str(html_value)
        for item in _SDDeltaItemsSorter(
            _EMPTY_NODE_HINT,
            _PaintValueAndRawValue,
            ImmutableDeltaAttributes(pairs={SDKey("ratio"): SDDeltaValue(old=1.5, new=2.0)}),
            ImmutableDeltaTable(),
        ).sort_pairs()
        for html_value in item.compute_td_spec(0).html_values
    ] == [
        '<span class="invold">1.50 <span class="muted_text">(1.5)</span></span>',
        '<span class="invnew">2.00 <span class="muted_text">(2.0)</span></span>',
    ]


def _painted_change(
    paint_function: PaintFunctionFromAPI, old: SDValue, new: SDValue
) -> Sequence[str]:
    return [
        str(html_value)
        for html_value in _SDDeltaItem(
            key=SDKey("key"),
            title="Title",
            old=old,
            new=new,
            paint_function=paint_function,
        )
        .compute_td_spec(0)
        .html_values
    ]


@pytest.mark.parametrize(
    "unit, old, new, expected",
    [
        pytest.param(
            UnitFromAPI(IECNotationFromAPI("B")),
            3.123 * 2**30,
            3.124 * 2**30,
            [
                '<span class="invold">3.123 GiB</span>',
                '<span class="invnew">3.124 GiB</span>',
            ],
            id="change in the third decimal",
        ),
        pytest.param(
            UnitFromAPI(SINotationFromAPI("B")),
            1.5 * 10**12,
            1.5 * 10**12 + 10**7,
            [
                '<span class="invold">1.5 TB</span>',
                '<span class="invnew">1.50001 TB</span>',
            ],
            id="small change of a big number",
        ),
        pytest.param(
            UnitFromAPI(SINotationFromAPI("s")),
            0.0012345,
            0.0012346,
            [
                '<span class="invold">1.234 ms</span>',
                '<span class="invnew">1.235 ms</span>',
            ],
            id="small change of a small number",
        ),
        pytest.param(
            UnitFromAPI(DecimalNotationFromAPI(""), StrictPrecisionFromAPI(0)),
            1.5,
            2.5,
            ['<span class="invold">1.5</span>', '<span class="invnew">2.5</span>'],
            id="values rounding alike",
        ),
        pytest.param(
            UnitFromAPI(DecimalNotationFromAPI(""), StrictPrecisionFromAPI(0)),
            1.45,
            2.44,
            ['<span class="invold">1</span>', '<span class="invnew">2</span>'],
            id="values rounding apart",
        ),
        pytest.param(
            UnitFromAPI(IECNotationFromAPI("B")),
            5 * 2**40,
            5 * 2**40 + 1,
            [
                '<span class="invold">5 TiB</span>',
                '<span class="invnew">5.0000000000009 TiB</span>',
            ],
            id="increase beyond the digits of a label",
        ),
        pytest.param(
            UnitFromAPI(IECNotationFromAPI("B")),
            5 * 2**40 + 1,
            6 * 2**40,
            ['<span class="invold">5 TiB</span>', '<span class="invnew">6 TiB</span>'],
            id="change telling apart within the digits of a label",
        ),
        pytest.param(
            UnitFromAPI(DecimalNotationFromAPI("")),
            0.1 + 0.2,
            0.3,
            [
                '<span class="invold">0.30000000000000004</span>',
                '<span class="invnew">0.3</span>',
            ],
            id="change at the last digit of a float",
        ),
        pytest.param(
            UnitFromAPI(IECNotationFromAPI("B")),
            5 * 2**40 + 1,
            5 * 2**40,
            [
                '<span class="invold">5.0000000000009 TiB</span>',
                '<span class="invnew">5 TiB</span>',
            ],
            id="decrease beyond the digits of a label",
        ),
        pytest.param(
            UnitFromAPI(AgeNotationFromAPI()),
            -(10**8),
            -(10**8) + 1,
            [
                '<span class="invold">3 y 62 d</span>',
                '<span class="invnew">3 y 62 d <span class="muted_text">(-1 s)</span></span>',
            ],
            id="newer timestamp of an age in whole parts",
        ),
    ],
)
def test_change_of_a_unit_value_is_painted_with_the_digits_telling_both_apart(
    unit: UnitFromAPI, old: float, new: float, expected: Sequence[str]
) -> None:
    assert (
        _painted_change(
            _PaintNumber(NumberFieldFromAPI(TitleFromAPI("Value"), render=unit)), old, new
        )
        == expected
    )


@pytest.mark.parametrize(
    "paint_function, old, new, expected",
    [
        pytest.param(
            inv_paint_bytes,
            3354228736,
            3354228737,
            [
                '<span class="invold">3.123868942 GiB</span>',
                '<span class="invnew">3.123868943 GiB</span>',
            ],
            id="bytes increase with more digits",
        ),
        pytest.param(
            inv_paint_bytes,
            3354228737,
            3354228736,
            [
                '<span class="invold">3.123868943 GiB</span>',
                '<span class="invnew">3.123868942 GiB</span>',
            ],
            id="bytes decrease with more digits",
        ),
        pytest.param(
            inv_paint_generic,
            1.5,
            1.5001,
            ['<span class="invold">1.5</span>', '<span class="invnew">1.5001</span>'],
            id="generic number with more digits",
        ),
        pytest.param(
            inv_paint_volt,
            12.31,
            12.34,
            ['<span class="invold">12.31 V</span>', '<span class="invnew">12.34 V</span>'],
            id="voltage with more digits",
        ),
        pytest.param(
            inv_paint_age,
            60.2,
            60.4,
            [
                '<span class="invold">60 s</span>',
                '<span class="invnew">60 s <span class="muted_text">(+200 ms)</span></span>',
            ],
            id="age",
        ),
        pytest.param(
            inv_paint_date,
            1762700000,
            1762700060,
            [
                f'<span class="invold">{inv_paint_date(1762700000)[1]}</span>',
                (
                    f'<span class="invnew">{inv_paint_date(1762700060)[1]} '
                    '<span class="muted_text">(+60 s)</span></span>'
                ),
            ],
            id="date",
        ),
        pytest.param(
            inv_paint_date_and_time,
            1762700000.25,
            1762700000.75,
            [
                f'<span class="invold">{inv_paint_date_and_time(1762700000.25)[1]}</span>',
                (
                    f'<span class="invnew">{inv_paint_date_and_time(1762700000.75)[1]} '
                    '<span class="muted_text">(+500 ms)</span></span>'
                ),
            ],
            id="date and time",
        ),
        pytest.param(
            inv_paint_generic,
            "a",
            "a ",
            ['<span class="invold">a</span>', '<span class="invnew">a </span>'],
            id="text",
        ),
    ],
)
def test_change_of_a_legacy_value_painted_alike_shows_the_difference(
    paint_function: PaintFunction, old: SDValue, new: SDValue, expected: Sequence[str]
) -> None:
    assert _painted_change(_PaintFunctionAdapter(paint_function), old, new) == expected


def test_change_of_a_rendered_number_painted_alike_shows_the_difference() -> None:
    assert _painted_change(
        _PaintNumber(NumberFieldFromAPI(TitleFromAPI("Date"), render=lambda _value: "2025-11-09")),
        1762700000,
        1762700060,
    ) == [
        '<span class="invold">2025-11-09</span>',
        '<span class="invnew">2025-11-09 <span class="muted_text">(+60)</span></span>',
    ]
