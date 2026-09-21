#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.inventory.delta import SDDeltaValue
from cmk.inventory.filtering import (
    filter_delta_tree,
    filter_tree,
    make_filter_choices_from_api_request_paths,
    SDFilterChoice,
)
from cmk.inventory.structured_data import SDKey, SDNodeName

from ._fixtures import (
    filled_delta_tree,
    filled_immutable_tree,
    filled_mutable_tree,
    immutable_tree,
)


def test_filter_delta_tree_nt() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("nt")),
                pairs=[SDKey("nt1")],
                columns=[SDKey("nt1")],
                nodes="nothing",
            )
        ],
    )

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))) == 0

    filtered_child = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))
    assert len(filtered_child) == 2
    assert filtered_child.path == ("path-to-nta", "nt")
    assert not filtered_child.attributes.pairs
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"nt1": SDDeltaValue(old=None, new="NT 01")},
        {"nt1": SDDeltaValue(old=None, new="NT 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_na() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("na")),
                pairs=[SDKey("na1")],
                columns=[SDKey("na1")],
                nodes="nothing",
            )
        ],
    )

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))) == 0

    filtered_child = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))
    assert len(filtered_child) == 1
    assert filtered_child.path == ("path-to-nta", "na")
    assert filtered_child.attributes.pairs == {"na1": SDDeltaValue(old=None, new="NA 1")}
    assert filtered_child.table.rows == []


def test_filter_delta_tree_ta() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta1")],
                columns=[SDKey("ta1")],
                nodes="nothing",
            )
        ],
    )

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0

    filtered_child = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(filtered_child) == 3
    assert filtered_child.path == ("path-to-nta", "ta")
    assert filtered_child.attributes.pairs == {"ta1": SDDeltaValue(old=None, new="TA 1")}
    assert len(filtered_child.table.rows) == 2
    for row in (
        {"ta1": SDDeltaValue(old=None, new="TA 01")},
        {"ta1": SDDeltaValue(old=None, new="TA 11")},
    ):
        assert row in filtered_child.table.rows


def test_filter_delta_tree_nta_ta() -> None:
    filtered = filter_delta_tree(
        filled_delta_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta0")],
                columns=[SDKey("ta0")],
                nodes="nothing",
            ),
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="nothing",
                columns=[SDKey("ta1")],
                nodes="nothing",
            ),
        ],
    )

    nta = filtered.get_tree((SDNodeName("path-to-nta"),))
    assert len(nta) == 5
    assert not nta.attributes.pairs
    assert nta.table.rows == []

    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0

    filtered_ta = filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(filtered_ta) == 5
    assert filtered_ta.attributes.pairs == {"ta0": SDDeltaValue(old=None, new="TA 0")}
    assert len(filtered_ta.table.rows) == 2
    for row in (
        {"ta0": SDDeltaValue(old=None, new="TA 00"), "ta1": SDDeltaValue(old=None, new="TA 01")},
        {"ta0": SDDeltaValue(old=None, new="TA 10"), "ta1": SDDeltaValue(old=None, new="TA 11")},
    ):
        assert row in filtered_ta.table.rows


def test_filter_tree_no_paths() -> None:
    assert len(filter_tree(filled_immutable_tree(), [])) == 0


def test_filter_tree_wrong_node() -> None:
    filtered = filter_tree(
        filled_immutable_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ],
    )
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("ta")))) == 6


def test_filter_tree_paths_no_keys() -> None:
    filtered = filter_tree(
        filled_immutable_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ],
    )

    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta0"))
        == "TA 0"
    )
    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta1"))
        == "TA 1"
    )
    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("foo")) is None
    )

    rows = filtered.get_rows((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(rows) == 2
    for row in [
        {"ta0": "TA 00", "ta1": "TA 01"},
        {"ta0": "TA 10", "ta1": "TA 11"},
    ]:
        assert row in rows


def test_filter_tree_paths_and_keys() -> None:
    filtered = filter_tree(
        filled_immutable_tree(),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta1")],
                columns=[SDKey("ta1")],
                nodes="all",
            ),
        ],
    )

    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("ta1"))
        == "TA 1"
    )
    assert (
        filtered.get_attribute((SDNodeName("path-to-nta"), SDNodeName("ta")), SDKey("foo")) is None
    )

    rows = filtered.get_rows((SDNodeName("path-to-nta"), SDNodeName("ta")))
    assert len(rows) == 2
    for row in [
        {"ta1": "TA 01"},
        {"ta1": "TA 11"},
    ]:
        assert row in rows


def test_filter_tree_mixed() -> None:
    filled_root_ = filled_mutable_tree()
    filled_root_.add(
        path=(SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node1")),
        pairs=[{SDKey("ak11"): "Another value 11", SDKey("ak12"): "Another value 12"}],
    )
    filled_root_.add(
        path=(SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node2")),
        key_columns=[SDKey("ak21")],
        rows=[
            {
                SDKey("ak21"): "Another value 211",
                SDKey("ak22"): "Another value 212",
            },
            {
                SDKey("ak21"): "Another value 221",
                SDKey("ak22"): "Another value 222",
            },
        ],
    )

    filtered = filter_tree(
        immutable_tree(filled_root_),
        [
            SDFilterChoice(
                path=(SDNodeName("path-to"), SDNodeName("another")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
            SDFilterChoice(
                path=(SDNodeName("path-to-nta"), SDNodeName("ta")),
                pairs=[SDKey("ta0")],
                columns=[SDKey("ta1")],
                nodes="all",
            ),
        ],
    )

    assert len(filtered) == 9
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("nt")))) == 0
    assert len(filtered.get_tree((SDNodeName("path-to-nta"), SDNodeName("na")))) == 0
    assert (
        len(filtered.get_tree((SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node1"))))
        == 2
    )
    assert (
        len(filtered.get_tree((SDNodeName("path-to"), SDNodeName("another"), SDNodeName("node2"))))
        == 4
    )


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        # Tuple format
        (
            ".path.to.node.",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:*.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
        (
            ".path.to.node.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
    ],
)
def test__make_filter_choices_from_api_request_paths(
    entry: str, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_api_request_paths([entry])[0] == expected_filter_choice
