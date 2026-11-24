#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.inventory.delta import ImmutableDeltaTree
from cmk.inventory.filtering import (
    filter_tree,
    SDFilterChoice,
)
from cmk.inventory.trees import ImmutableTree, SDKey, SDNodeName

from ._fixtures import inventory_store


def _size(tree: ImmutableTree | ImmutableDeltaTree, *names: str) -> int:
    return len(tree.get_tree(tuple(SDNodeName(n) for n in names)))


@pytest.mark.parametrize(
    "filters, unavail",
    [
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("hardware"), SDNodeName("components")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
                SDFilterChoice(
                    path=(SDNodeName("software"), SDNodeName("os")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
            ],
            [("hardware", "system"), ("software", "applications")],
        ),
    ],
)
def test_filter_real_tree_drops_the_unchosen_nodes(
    filters: Sequence[SDFilterChoice],
    unavail: Sequence[tuple[str, str]],
) -> None:
    tree = inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces"))
    filtered = filter_tree(tree, filters)
    assert (tree == filtered, [_size(filtered, *path) for path in unavail]) == (
        False,
        [0] * len(unavail),
    )


@pytest.mark.parametrize(
    "filters, amount_if_entries",
    [
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"),),
                    pairs="all",
                    columns="all",
                    nodes="all",
                )
            ],
            3178,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"),),
                    pairs=(
                        [
                            SDKey("total_interfaces"),
                            SDKey("total_ethernet_ports"),
                            SDKey("available_ethernet_ports"),
                        ]
                    ),
                    columns=(
                        [
                            SDKey("total_interfaces"),
                            SDKey("total_ethernet_ports"),
                            SDKey("available_ethernet_ports"),
                        ]
                    ),
                    nodes="nothing",
                ),
            ],
            0,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs="all",
                    columns="all",
                    nodes="all",
                ),
            ],
            3178,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status")],
                    columns=[SDKey("admin_status")],
                    nodes="nothing",
                ),
            ],
            326,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("FOOBAR")],
                    columns=[SDKey("admin_status"), SDKey("FOOBAR")],
                    nodes="nothing",
                ),
            ],
            326,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("oper_status")],
                    columns=[SDKey("admin_status"), SDKey("oper_status")],
                    nodes="nothing",
                ),
            ],
            652,
        ),
        (
            [
                SDFilterChoice(
                    path=(SDNodeName("networking"), SDNodeName("interfaces")),
                    pairs=[SDKey("admin_status"), SDKey("oper_status"), SDKey("FOOBAR")],
                    columns=[SDKey("admin_status"), SDKey("oper_status"), SDKey("FOOBAR")],
                    nodes="nothing",
                ),
            ],
            652,
        ),
    ],
)
def test_filter_networking_tree_keeps_only_networking(
    filters: Sequence[SDFilterChoice],
    amount_if_entries: int,
) -> None:
    filtered = filter_tree(
        inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
        filters,
    )
    assert (
        _size(filtered, "networking") > 0,
        _size(filtered, "hardware"),
        _size(filtered, "software"),
        _size(filtered, "networking", "interfaces"),
    ) == (True, 0, 0, amount_if_entries)


def test_filter_networking_tree_with_nothing_chosen_is_empty() -> None:
    filtered = filter_tree(
        inventory_store().load_inventory_tree(host_name=HostName("tree_new_interfaces")),
        [
            SDFilterChoice(
                path=(SDNodeName("networking"),),
                pairs="nothing",
                columns="nothing",
                nodes="nothing",
            ),
        ],
    )
    assert (
        _size(filtered, "networking"),
        _size(filtered, "hardware"),
        _size(filtered, "software"),
    ) == (0, 0, 0)
