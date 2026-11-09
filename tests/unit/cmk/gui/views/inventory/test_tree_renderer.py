#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.utils.structured_data import (
    ImmutableAttributes,
    ImmutableDeltaAttributes,
    ImmutableDeltaTable,
    ImmutableTable,
    RetentionInterval,
    SDDeltaValue,
    SDKey,
    SDPath,
    SDValue,
)

from cmk.gui.inventory.filters import FilterInvtableText
from cmk.gui.views.inventory._display_hints import (
    AttributeDisplayHint,
    ColumnDisplayHint,
    NodeDisplayHint,
)
from cmk.gui.views.inventory._paint_functions import (
    inv_paint_age,
    inv_paint_bytes,
    inv_paint_date,
    inv_paint_date_and_time,
    inv_paint_generic,
    inv_paint_timestamp_as_age,
    inv_paint_volt,
)
from cmk.gui.views.inventory._tree_renderer import (
    _render_legacy_difference,
    _replace_title_placeholders,
    _SDDeltaItem,
    _SDDeltaItemsSorter,
    _SDItemsSorter,
    SDItem,
)
from cmk.gui.views.inventory.registry import PaintFunction


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
                        key="sid",
                        title="SID",
                        value="SID 1",
                        retention_interval=None,
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key="flashback",
                        title="Flashback",
                        value="Flashback 1",
                        retention_interval=None,
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key="other",
                        title="Other",
                        value="Other 1",
                        retention_interval=None,
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                ],
                [
                    SDItem(
                        key="sid",
                        title="SID",
                        value="SID 2",
                        retention_interval=RetentionInterval(1, 2, 3, "previous"),
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key="flashback",
                        title="Flashback",
                        value="Flashback 2",
                        retention_interval=None,
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key="other",
                        title="Other",
                        value="Other 2",
                        retention_interval=None,
                        paint_function=inv_paint_generic,
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
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={},
            columns={
                SDKey("sid"): ColumnDisplayHint(
                    "SID", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("changed"): ColumnDisplayHint(
                    "Changed", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("foo"): ColumnDisplayHint(
                    "Foo", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("flashback"): ColumnDisplayHint(
                    "Flashback", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("other"): ColumnDisplayHint(
                    "Other", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
            },
            table_view_name="",
            table_is_show_more=True,
        ),
        "",
        ImmutableAttributes(),
        table,
    )
    assert items_sorter.sort_rows()[-1] == expected


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
                        key="sid",
                        title="SID",
                        old="SID 2",
                        new="SID 2",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key="flashback",
                        title="Flashback",
                        old="Flashback 21",
                        new="Flashback 22",
                        paint_function=inv_paint_generic,
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
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 11",
                        new="Changed 12",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 1",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 1",
                        new="Other 1",
                        paint_function=inv_paint_generic,
                    ),
                ],
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 2",
                        new=None,
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 21",
                        new="Changed 22",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 2",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 2",
                        new="Other 2",
                        paint_function=inv_paint_generic,
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
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 11",
                        new="Changed 12",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 1",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 1",
                        new="Other 1",
                        paint_function=inv_paint_generic,
                    ),
                ],
                [
                    _SDDeltaItem(
                        key=SDKey("sid"),
                        title="SID",
                        old="SID 2",
                        new=None,
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("changed"),
                        title="Changed",
                        old="Changed 21",
                        new="Changed 22",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("flashback"),
                        title="Flashback",
                        old=None,
                        new="Flashback 2",
                        paint_function=inv_paint_generic,
                    ),
                    _SDDeltaItem(
                        key=SDKey("other"),
                        title="Other",
                        old="Other 2",
                        new="Other 2",
                        paint_function=inv_paint_generic,
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
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={},
            columns={
                SDKey("sid"): ColumnDisplayHint(
                    "SID", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("changed"): ColumnDisplayHint(
                    "Changed", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("foo"): ColumnDisplayHint(
                    "Foo", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("flashback"): ColumnDisplayHint(
                    "Flashback", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
                SDKey("other"): ColumnDisplayHint(
                    "Other", "", "", inv_paint_generic, lambda r, l: 0, FilterInvtableText
                ),
            },
            table_view_name="",
            table_is_show_more=True,
        ),
        ImmutableDeltaAttributes(),
        delta_table,
    )
    assert delta_items_sorter.sort_rows()[-1] == expected


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
                    paint_function=inv_paint_generic,
                    icon_path_svc_problems="",
                ),
                SDItem(
                    key=SDKey("b"),
                    title="B",
                    value="B",
                    retention_interval=None,
                    paint_function=inv_paint_generic,
                    icon_path_svc_problems="",
                ),
                SDItem(
                    key=SDKey("d"),
                    title="D",
                    value="D",
                    retention_interval=None,
                    paint_function=inv_paint_generic,
                    icon_path_svc_problems="",
                ),
                SDItem(
                    key=SDKey("c"),
                    title="C",
                    value="C",
                    retention_interval=RetentionInterval(1, 2, 3, "previous"),
                    paint_function=inv_paint_generic,
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
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={
                SDKey("a"): AttributeDisplayHint(
                    "A", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
                SDKey("b"): AttributeDisplayHint(
                    "B", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
                SDKey("d"): AttributeDisplayHint(
                    "D", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
                SDKey("c"): AttributeDisplayHint(
                    "C", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
            },
            columns={},
            table_view_name="",
            table_is_show_more=True,
        ),
        "",
        attributes,
        ImmutableTable(),
    )
    assert items_sorter.sort_pairs() == expected


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
                    paint_function=inv_paint_generic,
                ),
                _SDDeltaItem(
                    key=SDKey("b"),
                    title="B",
                    old="B",
                    new=None,
                    paint_function=inv_paint_generic,
                ),
                _SDDeltaItem(
                    key=SDKey("d"),
                    title="D",
                    old=None,
                    new="D",
                    paint_function=inv_paint_generic,
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
            path=(),
            icon="",
            title="",
            short_title="",
            long_title="",
            attributes={
                SDKey("a"): AttributeDisplayHint(
                    "A", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
                SDKey("b"): AttributeDisplayHint(
                    "B", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
                SDKey("d"): AttributeDisplayHint(
                    "D", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
                SDKey("c"): AttributeDisplayHint(
                    "C", "", "", inv_paint_generic, lambda r, l: 0, "", False
                ),
            },
            columns={},
            table_view_name="",
            table_is_show_more=True,
        ),
        delta_attributes,
        ImmutableDeltaTable(),
    )
    assert delta_items_sorter.sort_pairs() == expected


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
                path=abc_path,
                icon="",
                title=title,
                short_title=title,
                long_title=title,
                attributes={},
                columns={},
                table_view_name="",
                table_is_show_more=True,
            ),
            path,
        )
        == expected_title
    )


@pytest.mark.parametrize(
    "paint_function, old, new, expected",
    [
        pytest.param(
            inv_paint_bytes,
            3354228736,
            3354228737,
            '<span class="invold">3.123868942 GiB</span> → '
            '<span class="invnew">3.123868943 GiB</span>',
            id="bytes increase with more digits",
        ),
        pytest.param(
            inv_paint_bytes,
            3354228737,
            3354228736,
            '<span class="invold">3.123868943 GiB</span> → '
            '<span class="invnew">3.123868942 GiB</span>',
            id="bytes decrease with more digits",
        ),
        pytest.param(
            inv_paint_generic,
            1.5,
            1.5001,
            '<span class="invold">1.5</span> → <span class="invnew">1.5001</span>',
            id="generic number with more digits",
        ),
        pytest.param(
            inv_paint_volt,
            12.31,
            12.34,
            '<span class="invold">12.31 V</span> → <span class="invnew">12.34 V</span>',
            id="voltage with more digits",
        ),
        pytest.param(
            inv_paint_age,
            60.2,
            60.4,
            '<span class="invold">60 s</span> → '
            '<span class="invnew">60 s <span class="muted_text">(+200 ms)</span></span>',
            id="age",
        ),
        pytest.param(
            inv_paint_date,
            1762700000,
            1762700060,
            f'<span class="invold">{inv_paint_date(1762700000)[1]}</span> → '
            f'<span class="invnew">{inv_paint_date(1762700060)[1]} '
            '<span class="muted_text">(+60 s)</span></span>',
            id="date",
        ),
        pytest.param(
            inv_paint_date_and_time,
            1762700000.25,
            1762700000.75,
            f'<span class="invold">{inv_paint_date_and_time(1762700000.25)[1]}</span> → '
            f'<span class="invnew">{inv_paint_date_and_time(1762700000.75)[1]} '
            '<span class="muted_text">(+500 ms)</span></span>',
            id="date and time",
        ),
        pytest.param(
            inv_paint_generic,
            "a",
            "a ",
            '<span class="invold">a</span> → <span class="invnew">a </span>',
            id="text",
        ),
    ],
)
def test_change_painted_alike_shows_the_difference(
    paint_function: PaintFunction, old: SDValue, new: SDValue, expected: str
) -> None:
    assert (
        str(
            _SDDeltaItem(
                key=SDKey("key"),
                title="Title",
                old=old,
                new=new,
                paint_function=paint_function,
            ).compute_cell_spec()[2]
        )
        == expected
    )


def test_newer_timestamp_shown_as_age_is_a_smaller_age() -> None:
    assert _render_legacy_difference(inv_paint_timestamp_as_age, 60) == "-60 s"
