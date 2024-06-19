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
)

from cmk.gui.views.inventory._display_hints import AttributeDisplayHint, NodeDisplayHint
from cmk.gui.views.inventory._paint_functions import inv_paint_generic
from cmk.gui.views.inventory._tree_renderer import (
    _replace_title_placeholders,
    _SDDeltaItem,
    _sort_delta_pairs,
    _sort_delta_rows,
    _sort_pairs,
    _sort_rows,
    Column,
    SDItem,
)


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
                    (None,): {SDKey("sid"): None, SDKey("flashback"): None, SDKey("other"): None},
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
                        key="changed",
                        title="Changed",
                        value=None,
                        retention_interval=None,
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key="foo",
                        title="Foo",
                        value=None,
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
                        key="changed",
                        title="Changed",
                        value=None,
                        retention_interval=None,
                        paint_function=inv_paint_generic,
                        icon_path_svc_problems="",
                    ),
                    SDItem(
                        key="foo",
                        title="Foo",
                        value=None,
                        retention_interval=None,
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
    columns = [
        Column(key=SDKey("sid"), title="SID", paint_function=inv_paint_generic, key_info=""),
        Column(
            key=SDKey("changed"), title="Changed", paint_function=inv_paint_generic, key_info=""
        ),
        Column(key=SDKey("foo"), title="Foo", paint_function=inv_paint_generic, key_info=""),
        Column(
            key=SDKey("flashback"), title="Flashback", paint_function=inv_paint_generic, key_info=""
        ),
        Column(key=SDKey("other"), title="Other", paint_function=inv_paint_generic, key_info=""),
    ]
    assert _sort_rows(table, columns, "") == expected


@pytest.mark.parametrize(
    "delta_table, expected",
    [
        (ImmutableDeltaTable(), []),
        (
            ImmutableDeltaTable(
                key_columns=[SDKey("sid")],
                rows=[
                    {
                        SDKey("sid"): SDDeltaValue("SID 2", None),
                        SDKey("flashback"): SDDeltaValue(None, "Flashback 2"),
                        SDKey("other"): SDDeltaValue("Other 2", "Other 2"),
                        SDKey("changed"): SDDeltaValue("Changed 21", "Changed 22"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue("SID 1", None),
                        SDKey("flashback"): SDDeltaValue(None, "Flashback 1"),
                        SDKey("other"): SDDeltaValue("Other 1", "Other 1"),
                        SDKey("changed"): SDDeltaValue("Changed 11", "Changed 12"),
                    },
                    {
                        SDKey("sid"): SDDeltaValue("SID 3", "SID 3"),
                        SDKey("flashback"): SDDeltaValue("Flashback 3", "Flashback 3"),
                        SDKey("other"): SDDeltaValue(None, None),
                        SDKey("changed"): SDDeltaValue(None, None),
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
                        key=SDKey("foo"),
                        title="Foo",
                        old=None,
                        new=None,
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
                        key=SDKey("foo"),
                        title="Foo",
                        old=None,
                        new=None,
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
def test_sort_deltatable_rows_displayhint(
    delta_table: ImmutableDeltaTable,
    expected: Sequence[Sequence[_SDDeltaItem]],
) -> None:
    columns = [
        Column(key=SDKey("sid"), title="SID", paint_function=inv_paint_generic, key_info=""),
        Column(
            key=SDKey("changed"), title="Changed", paint_function=inv_paint_generic, key_info=""
        ),
        Column(key=SDKey("foo"), title="Foo", paint_function=inv_paint_generic, key_info=""),
        Column(
            key=SDKey("flashback"), title="Flashback", paint_function=inv_paint_generic, key_info=""
        ),
        Column(key=SDKey("other"), title="Other", paint_function=inv_paint_generic, key_info=""),
    ]
    assert _sort_delta_rows(delta_table, columns) == expected


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
    hint = NodeDisplayHint(
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
    )
    assert _sort_pairs(attributes, hint, "") == expected


@pytest.mark.parametrize(
    "delta_attributes, expected",
    [
        (ImmutableDeltaAttributes(), []),
        (
            ImmutableDeltaAttributes(
                pairs={
                    SDKey("b"): SDDeltaValue("B", None),
                    SDKey("d"): SDDeltaValue(None, "D"),
                    SDKey("c"): SDDeltaValue("C", "C"),
                    SDKey("a"): SDDeltaValue("A1", "A2"),
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
                _SDDeltaItem(
                    key=SDKey("c"),
                    title="C",
                    old="C",
                    new="C",
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
    hint = NodeDisplayHint(
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
    )
    assert _sort_delta_pairs(delta_attributes, hint) == expected


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
