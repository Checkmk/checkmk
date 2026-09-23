#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence

import pytest

from cmk.gui.inventory.filters import (
    _find_package,
    FilterInvBool,
    FilterInvFloat,
    FilterInvFloatChoice,
)
from cmk.gui.type_defs import Rows, VisualContext
from cmk.inventory.raw_paths import InventoryPath, TreeSource
from cmk.inventory.trees import (
    ImmutableAttributes,
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


_PACKAGE_A = {"name": "package-a", "version": "2.0"}


@pytest.mark.parametrize(
    "packages, name, from_version, to_version, expected",
    [
        pytest.param([_PACKAGE_A], "package-a", "", "", True, id="name-without-bounds"),
        pytest.param([_PACKAGE_A], "package-b", "", "", False, id="another-name"),
        pytest.param([], "package-a", "", "", False, id="no-packages"),
        pytest.param([_PACKAGE_A], "package-a", "2.0", "2.0", True, id="the-exact-version"),
        pytest.param([_PACKAGE_A], "package-a", "3.0", "3.0", False, id="another-exact-version"),
        pytest.param([_PACKAGE_A], "package-a", "1.0", "", True, id="above-the-lower-bound"),
        pytest.param([_PACKAGE_A], "package-a", "3.0", "", False, id="below-the-lower-bound"),
        pytest.param([_PACKAGE_A], "package-a", "", "3.0", True, id="below-the-upper-bound"),
        pytest.param([_PACKAGE_A], "package-a", "", "1.0", False, id="above-the-upper-bound"),
        pytest.param([_PACKAGE_A], "package-a", "1.0", "3.0", True, id="between-the-bounds"),
        pytest.param([_PACKAGE_A], "package-a", "3.0", "4.0", False, id="beneath-the-bounds"),
        pytest.param(
            [_PACKAGE_A], re.compile("^package"), "", "", True, id="a-regex-matching-the-name"
        ),
        pytest.param(
            [_PACKAGE_A], re.compile("^other"), "", "", False, id="a-regex-matching-no-name"
        ),
        pytest.param(
            [{"name": "package-a", "version": "1.0"}],
            "package-a",
            "1.00",
            "",
            True,
            id="the-lower-bound-spelled-with-another-zero",
        ),
        pytest.param(
            [{"name": "package-a", "version": "1.0"}],
            "package-a",
            "",
            "1.00",
            True,
            id="the-upper-bound-spelled-with-another-zero",
        ),
    ],
)
def test_find_package(
    packages: Sequence[Mapping[str, SDValue]],
    name: str | re.Pattern[str],
    from_version: str,
    to_version: str,
    expected: bool,
) -> None:
    assert _find_package(packages, name, from_version, to_version) is expected
