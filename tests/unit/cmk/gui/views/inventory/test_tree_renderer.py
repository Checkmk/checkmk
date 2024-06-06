#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict
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

from cmk.gui.views.inventory._display_hints import NodeDisplayHint
from cmk.gui.views.inventory._tree_renderer import (
    _replace_title_placeholders,
    _SDDeltaItem,
    _sort_delta_pairs,
    _sort_delta_rows,
    _sort_pairs,
    _sort_rows,
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
                    SDItem("sid", "SID 1", None),
                    SDItem("changed", None, None),
                    SDItem("foo", None, None),
                    SDItem("flashback", "Flashback 1", None),
                    SDItem("other", "Other 1", None),
                ],
                [
                    SDItem("sid", "SID 2", RetentionInterval(1, 2, 3, "previous")),
                    SDItem("changed", None, None),
                    SDItem("foo", None, None),
                    SDItem("flashback", "Flashback 2", None),
                    SDItem("other", "Other 2", None),
                ],
            ],
        ),
    ],
)
def test_sort_table_rows_displayhint(
    table: ImmutableTable,
    expected: Sequence[Sequence[SDItem]],
) -> None:
    assert (
        _sort_rows(
            table,
            [SDKey("sid"), SDKey("changed"), SDKey("foo"), SDKey("flashback"), SDKey("other")],
        )
        == expected
    )


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
                    _SDDeltaItem(SDKey("sid"), "SID 1", None),
                    _SDDeltaItem(SDKey("changed"), "Changed 11", "Changed 12"),
                    _SDDeltaItem(SDKey("foo"), None, None),
                    _SDDeltaItem(SDKey("flashback"), None, "Flashback 1"),
                    _SDDeltaItem(SDKey("other"), "Other 1", "Other 1"),
                ],
                [
                    _SDDeltaItem(SDKey("sid"), "SID 2", None),
                    _SDDeltaItem(SDKey("changed"), "Changed 21", "Changed 22"),
                    _SDDeltaItem(SDKey("foo"), None, None),
                    _SDDeltaItem(SDKey("flashback"), None, "Flashback 2"),
                    _SDDeltaItem(SDKey("other"), "Other 2", "Other 2"),
                ],
            ],
        ),
    ],
)
def test_sort_deltatable_rows_displayhint(
    delta_table: ImmutableDeltaTable,
    expected: Sequence[Sequence[_SDDeltaItem]],
) -> None:
    assert (
        _sort_delta_rows(
            delta_table,
            [SDKey("sid"), SDKey("changed"), SDKey("foo"), SDKey("flashback"), SDKey("other")],
        )
        == expected
    )


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
                SDItem(SDKey("a"), "A", None),
                SDItem(SDKey("b"), "B", None),
                SDItem(SDKey("d"), "D", None),
                SDItem(SDKey("c"), "C", RetentionInterval(1, 2, 3, "previous")),
            ],
        ),
    ],
)
def test_sort_attributes_pairs_displayhint(
    attributes: ImmutableAttributes,
    expected: Sequence[SDItem],
) -> None:
    assert _sort_pairs(attributes, [SDKey("a"), SDKey("b"), SDKey("d"), SDKey("c")]) == expected


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
                _SDDeltaItem(SDKey("a"), "A1", "A2"),
                _SDDeltaItem(SDKey("b"), "B", None),
                _SDDeltaItem(SDKey("d"), None, "D"),
                _SDDeltaItem(SDKey("c"), "C", "C"),
            ],
        ),
    ],
)
def test_sort_delta_attributes_pairs_displayhint(
    delta_attributes: ImmutableDeltaAttributes,
    expected: Sequence[_SDDeltaItem],
) -> None:
    assert (
        _sort_delta_pairs(delta_attributes, [SDKey("a"), SDKey("b"), SDKey("d"), SDKey("c")])
        == expected
    )


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
                attributes=OrderedDict(),
                columns=OrderedDict(),
                table_view_name="",
                table_is_show_more=True,
            ),
            path,
        )
        == expected_title
    )
