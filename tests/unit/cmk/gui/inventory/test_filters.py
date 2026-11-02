#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.inventory.filters import (
    FilterInvBool,
    FilterInvChoice,
    FilterInvFloat,
    FilterInvFloatChoice,
    FilterInvHasSoftwarePackage,
    FilterInvtableTextWithSortKey,
    FilterInvText,
    FilterInvTextWithSortKey,
)
from cmk.gui.type_defs import Row, Rows, VisualContext
from cmk.inventory.raw_paths import InventoryPath, TreeSource
from cmk.inventory.trees import (
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    SDKey,
    SDNodeName,
    SDValue,
)


def _make_host_inventory_tree(value: SDValue) -> ImmutableTree:
    return ImmutableTree(
        nodes_by_name={
            SDNodeName("path-to-node"): ImmutableTree(
                attributes=ImmutableAttributes(pairs={SDKey("key"): value})
            )
        }
    )


@pytest.mark.parametrize(
    "context, rows, expected_rows",
    [
        pytest.param(
            {},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            id="no-context",
        ),
        pytest.param(
            {"ident": {}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            id="no-http-filter-vars",
        ),
        pytest.param(
            {"ident": {"ident_from": "2"}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            id="from",
        ),
        pytest.param(
            {"ident": {"ident_until": "2"}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
            ],
            id="until",
        ),
        pytest.param(
            {"ident": {"ident_from": "2", "ident_until": "4"}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
                {"host_inventory": _make_host_inventory_tree(4)},
                {"host_inventory": _make_host_inventory_tree(5)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(3)},
                {"host_inventory": _make_host_inventory_tree(4)},
            ],
            id="from-until",
        ),
    ],
)
def test_filter_inv_float(context: VisualContext, rows: Rows, expected_rows: Rows) -> None:
    assert (
        FilterInvFloat(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
            unit_choices={},
        ).filter_table(context, rows)
        == expected_rows
    )


@pytest.mark.parametrize(
    "context, rows, expected_rows",
    [
        pytest.param(
            {"ident": {"ident_from": "2", "ident_from_prefix": "k"}},
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
            ],
            id="from",
        ),
        pytest.param(
            {"ident": {"ident_until": "2", "ident_until_prefix": "k"}},
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
            ],
            id="until",
        ),
        pytest.param(
            {
                "ident": {
                    "ident_from": "2",
                    "ident_from_prefix": "k",
                    "ident_until": "4",
                    "ident_until_prefix": "M",
                }
            },
            [
                {"host_inventory": _make_host_inventory_tree(10)},
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
                {"host_inventory": _make_host_inventory_tree(400)},
                {"host_inventory": _make_host_inventory_tree(500)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(20)},
                {"host_inventory": _make_host_inventory_tree(30)},
                {"host_inventory": _make_host_inventory_tree(400)},
            ],
            id="from-until",
        ),
    ],
)
def test_filter_inv_float_unit_choices(
    context: VisualContext, rows: Rows, expected_rows: Rows
) -> None:
    assert (
        FilterInvFloat(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
            unit_choices={
                "": FilterInvFloatChoice("U", 1),
                "k": FilterInvFloatChoice("kU", 10),
                "M": FilterInvFloatChoice("MU", 100),
            },
        ).filter_table(context, rows)
        == expected_rows
    )


@pytest.mark.parametrize(
    "context, rows, expected_rows",
    [
        pytest.param(
            {},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            id="no-context",
        ),
        pytest.param(
            {"ident": {"is_ident": "-1"}},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            id="ignore",
        ),
        pytest.param(
            {"ident": {"is_ident": "1"}},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(True)},
            ],
            id="select-true",
        ),
        pytest.param(
            {"ident": {"is_ident": "0"}},
            [
                {"host_inventory": _make_host_inventory_tree(True)},
                {"host_inventory": _make_host_inventory_tree(False)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
            [
                {"host_inventory": _make_host_inventory_tree(False)},
            ],
            id="select-false",
        ),
    ],
)
def test_filter_inv_bool(context: VisualContext, rows: Rows, expected_rows: Rows) -> None:
    assert (
        FilterInvBool(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
        ).filter_table(context, rows)
        == expected_rows
    )


@pytest.mark.parametrize(
    "context, expected_rows",
    [
        pytest.param(
            {},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
            id="no-context",
        ),
        pytest.param(
            {"ident": {"ident": ""}},
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
            id="ignore",
        ),
        pytest.param(
            {"ident": {"ident": "1"}},
            [{"host_inventory": _make_host_inventory_tree(1)}],
            id="select-first",
        ),
        pytest.param(
            {"ident": {"ident": "2"}},
            [{"host_inventory": _make_host_inventory_tree(2)}],
            id="select-last",
        ),
    ],
)
def test_filter_inv_choice(context: VisualContext, expected_rows: Rows) -> None:
    assert (
        FilterInvChoice(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
            options=[("1", "One"), ("2", "Two")],
        ).filter_table(
            context,
            [
                {"host_inventory": _make_host_inventory_tree(1)},
                {"host_inventory": _make_host_inventory_tree(2)},
                {"host_inventory": _make_host_inventory_tree(None)},
            ],
        )
        == expected_rows
    )


def test_filter_inv_text_skips_a_missing_attribute() -> None:
    assert FilterInvText(
        ident="ident",
        title="Title",
        inventory_path=InventoryPath(
            (SDNodeName("path-to-node"),),
            TreeSource.attributes,
            SDKey("key"),
        ),
    ).filter_table(
        {"ident": {"ident": "no"}},
        [
            {"host_inventory": _make_host_inventory_tree("Novell")},
            {"host_inventory": _make_host_inventory_tree(None)},
        ],
    ) == [{"host_inventory": _make_host_inventory_tree("Novell")}]


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param({}, False, id="no-bounds"),
        pytest.param({"ident_from": "a"}, True, id="from"),
        pytest.param({"ident_until": "a"}, True, id="until"),
        pytest.param({"ident_from": " ", "ident_until": " "}, False, id="blank-bounds"),
    ],
)
def test_filter_inv_text_with_sort_key_needs_inventory_for_any_bound(
    value: Mapping[str, str], expected: bool
) -> None:
    assert (
        FilterInvTextWithSortKey(
            ident="ident",
            title="Title",
            inventory_path=InventoryPath(
                (SDNodeName("path-to-node"),),
                TreeSource.attributes,
                SDKey("key"),
            ),
            sort_key=str,
        ).need_inventory(value)
        is expected
    )


@pytest.mark.parametrize(
    "context, expected_rows",
    [
        pytest.param({}, [{"ident": "a"}, {"ident": "b"}, {"ident": "c"}], id="no-bounds"),
        pytest.param({"ident": {"ident_from": "b"}}, [{"ident": "b"}, {"ident": "c"}], id="from"),
        pytest.param({"ident": {"ident_until": "b"}}, [{"ident": "a"}, {"ident": "b"}], id="until"),
        pytest.param(
            {"ident": {"ident_from": "b", "ident_until": "b"}}, [{"ident": "b"}], id="from-until"
        ),
    ],
)
def test_filter_invtable_text_with_sort_key_includes_its_bounds(
    context: VisualContext, expected_rows: Rows
) -> None:
    assert (
        FilterInvtableTextWithSortKey(
            inv_info="info",
            ident="ident",
            title="Title",
            sort_key=str,
        ).filter_table(context, [{"ident": "a"}, {"ident": "b"}, {"ident": "c"}])
        == expected_rows
    )


def _make_host_with_package(name: str) -> Row:
    return {
        "host_inventory": ImmutableTree(
            nodes_by_name={
                SDNodeName("software"): ImmutableTree(
                    nodes_by_name={
                        SDNodeName("packages"): ImmutableTree(
                            table=ImmutableTable(
                                key_columns=[SDKey("name")],
                                rows_by_ident={
                                    (name,): {SDKey("name"): name, SDKey("version"): "1.0"}
                                },
                            )
                        )
                    }
                )
            }
        )
    }


_HOST_WITH_PACKAGE_A = _make_host_with_package("package-a")
_HOST_WITH_PACKAGE_B = _make_host_with_package("package-b")
_HOST_WITHOUT_PACKAGES: Row = {"host_inventory": ImmutableTree()}


@pytest.mark.parametrize(
    "filter_vars, expected_rows",
    [
        pytest.param(
            {}, [_HOST_WITH_PACKAGE_A, _HOST_WITH_PACKAGE_B, _HOST_WITHOUT_PACKAGES], id="no-name"
        ),
        pytest.param({"invswpac_host_name": "package-a"}, [_HOST_WITH_PACKAGE_A], id="exact-name"),
        pytest.param({"invswpac_host_name": "package-c"}, [], id="another-name"),
        pytest.param(
            {"invswpac_host_name": "^package", "invswpac_host_match": "regex"},
            [_HOST_WITH_PACKAGE_A, _HOST_WITH_PACKAGE_B],
            id="a-regex-matching-names",
        ),
        pytest.param(
            {"invswpac_host_name": "^other", "invswpac_host_match": "regex"},
            [],
            id="a-regex-matching-no-name",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_negate": "on"},
            [_HOST_WITH_PACKAGE_B, _HOST_WITHOUT_PACKAGES],
            id="negate",
        ),
        pytest.param(
            {
                "invswpac_host_name": "package-a",
                "invswpac_host_version_from": "1.0",
                "invswpac_host_version_to": "1.0",
            },
            [_HOST_WITH_PACKAGE_A],
            id="the-exact-version",
        ),
        pytest.param(
            {
                "invswpac_host_name": "package-a",
                "invswpac_host_version_from": "2.0",
                "invswpac_host_version_to": "2.0",
            },
            [],
            id="another-exact-version",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_version_from": "0.5"},
            [_HOST_WITH_PACKAGE_A],
            id="above-the-lower-bound",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_version_from": "2.0"},
            [],
            id="below-the-lower-bound",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_version_to": "2.0"},
            [_HOST_WITH_PACKAGE_A],
            id="below-the-upper-bound",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_version_to": "0.5"},
            [],
            id="above-the-upper-bound",
        ),
        pytest.param(
            {
                "invswpac_host_name": "package-a",
                "invswpac_host_version_from": "0.5",
                "invswpac_host_version_to": "2.0",
            },
            [_HOST_WITH_PACKAGE_A],
            id="between-the-bounds",
        ),
        pytest.param(
            {
                "invswpac_host_name": "package-a",
                "invswpac_host_version_from": "2.0",
                "invswpac_host_version_to": "3.0",
            },
            [],
            id="beneath-the-bounds",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_version_from": "1.00"},
            [_HOST_WITH_PACKAGE_A],
            id="the-lower-bound-spelled-with-another-zero",
        ),
        pytest.param(
            {"invswpac_host_name": "package-a", "invswpac_host_version_to": "1.00"},
            [_HOST_WITH_PACKAGE_A],
            id="the-upper-bound-spelled-with-another-zero",
        ),
    ],
)
def test_filter_inv_has_software_package(
    filter_vars: Mapping[str, str], expected_rows: Rows
) -> None:
    assert (
        FilterInvHasSoftwarePackage().filter_table(
            {"invswpac": filter_vars},
            [_HOST_WITH_PACKAGE_A, _HOST_WITH_PACKAGE_B, _HOST_WITHOUT_PACKAGES],
        )
        == expected_rows
    )
