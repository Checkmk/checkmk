#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The kinds of relation two hosts can have, and which links this version can place."""

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.i18n import _l
from cmk.gui.utils.host_relation_kinds import (
    DirectedRelationKind,
    kind_accepts,
    known_relations,
    RELATION_KINDS,
    RelationEnd,
    SymmetricRelationKind,
)
from cmk.gui.utils.host_relations import RelationDirection, RelationLink


def test_the_kinds_this_version_knows() -> None:
    """Pinned: a kind id is stored, so adding one is a feature and renaming one is a migration."""
    assert set(RELATION_KINDS) == {"management"}


def test_a_kind_id_has_to_be_an_identifier() -> None:
    """It ends up in an element name of the host dialog, which rejects anything else."""
    with pytest.raises(ValueError):
        DirectedRelationKind(
            id="management board",
            parent=RelationEnd(row=_l("row"), noun=_l("noun")),
            child=RelationEnd(row=_l("row"), noun=_l("noun")),
        )


def test_a_directed_kind_has_two_ends_that_read_differently() -> None:
    kind = RELATION_KINDS["management"]
    assert isinstance(kind, DirectedRelationKind)

    assert tuple(kind.directions()) == ("parent", "child")
    assert kind.end("parent") is kind.parent
    assert kind.end("child") is kind.child
    assert str(kind.parent.noun) != str(kind.child.noun)


def test_a_directed_kind_has_no_symmetric_end() -> None:
    kind = RELATION_KINDS["management"]

    with pytest.raises(ValueError):
        kind.end("symmetric")


def test_a_symmetric_kind_reads_the_same_from_both_sides() -> None:
    peer = RelationEnd(row=_l("is peer of"), noun=_l("Peer"))
    kind = SymmetricRelationKind(id="peering", peer=peer)

    assert tuple(kind.directions()) == ("symmetric",)
    assert kind.end("symmetric") is peer


@pytest.mark.parametrize("direction", ["parent", "child"])
def test_a_symmetric_kind_has_no_directed_end(direction: RelationDirection) -> None:
    kind = SymmetricRelationKind(id="peering", peer=RelationEnd(row=_l("row"), noun=_l("noun")))

    with pytest.raises(ValueError):
        kind.end(direction)


@pytest.mark.parametrize(
    "kind_id, direction, accepted",
    [
        pytest.param("management", "parent", True, id="known kind, known end"),
        pytest.param("management", "child", True, id="known kind, other end"),
        pytest.param("management", "symmetric", False, id="known kind, end it does not have"),
        pytest.param("peering", "symmetric", False, id="kind of a later version"),
        pytest.param("", "parent", False, id="no kind at all"),
    ],
)
def test_a_link_can_only_be_placed_by_a_kind_that_has_such_an_end(
    kind_id: str, direction: RelationDirection, accepted: bool
) -> None:
    assert kind_accepts(kind_id, direction) is accepted


def test_the_links_this_version_can_place_keep_their_order() -> None:
    links: list[RelationLink] = [
        {"kind": "management", "direction": "child", "host": HostName("os1")},
        {"kind": "peering", "direction": "symmetric", "host": HostName("peer")},
        {"kind": "management", "direction": "symmetric", "host": HostName("odd")},
        {"kind": "management", "direction": "parent", "host": HostName("os2")},
    ]

    assert known_relations(links) == [
        {"kind": "management", "direction": "child", "host": HostName("os1")},
        {"kind": "management", "direction": "parent", "host": HostName("os2")},
    ]


def test_a_link_that_cannot_be_placed_is_reported_rather_than_dropped_silently() -> None:
    """A link of a later version must not cost a host the rest of its relations unnoticed."""
    unknown: list[RelationLink] = []
    links: list[RelationLink] = [
        {"kind": "peering", "direction": "symmetric", "host": HostName("peer")},
        {"kind": "management", "direction": "parent", "host": HostName("os1")},
    ]

    known_relations(links, on_unknown=unknown.append)

    assert unknown == [{"kind": "peering", "direction": "symmetric", "host": HostName("peer")}]
