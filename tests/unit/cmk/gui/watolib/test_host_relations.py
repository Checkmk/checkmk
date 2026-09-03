#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import cast

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.utils.host_relations import RelationDirection, ResolvedRelation
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.host_relations import RelatedHost, resolve_all_relations


class _FakeHost:
    """A host as ``resolve_all_relations`` sees it - it asks for nothing else.

    Satisfies :class:`RelatedHost`, so it needs no cast where the resolver is called.
    """

    def __init__(self, name: str, relations: object = None, site: str = "central") -> None:
        self._name = HostName(name)
        self._site = SiteId(site)
        self.attributes = cast(
            "HostAttributes", {} if relations is None else {"relations": relations}
        )

    def name(self) -> HostName:
        return self._name

    def site_id(self) -> SiteId:
        return self._site


def _hosts(**relations: object) -> Mapping[HostName, RelatedHost]:
    return {HostName(name): _FakeHost(name, value) for name, value in relations.items()}


@pytest.mark.parametrize("stored, mirrored", [("child", "parent"), ("parent", "child")])
def test_one_stored_half_materializes_on_both_sides(
    stored: RelationDirection, mirrored: RelationDirection
) -> None:
    """A dialog row reads "this host is OS host of <other>", and so does the value the core
    gets - from either end, and for a half whose counterpart row was lost as well: the
    monitoring is never one-sided, only Setup can be."""
    resolved = resolve_all_relations(
        _hosts(srv=[{"kind": "management", "direction": stored, "host": "board"}], board=None)
    )

    assert resolved[HostName("srv")] == [
        ResolvedRelation(kind="management", direction=stored, host="board", site="central")
    ]
    assert resolved[HostName("board")] == [
        ResolvedRelation(kind="management", direction=mirrored, host="srv", site="central")
    ]


def test_resolve_all_relations_carries_the_site_of_the_counterpart() -> None:
    """Only the central site knows where a host is monitored, so the site travels along."""
    all_hosts: Mapping[HostName, RelatedHost] = {
        HostName("board"): _FakeHost(
            "board", [{"kind": "management", "direction": "parent", "host": "os1"}]
        ),
        HostName("os1"): _FakeHost("os1", site="remote"),
    }

    resolved = resolve_all_relations(all_hosts)

    assert resolved[HostName("board")] == [
        ResolvedRelation(kind="management", direction="parent", host="os1", site="remote")
    ]
    assert resolved[HostName("os1")] == [
        ResolvedRelation(kind="management", direction="child", host="board", site="central")
    ]


def test_both_sides_storing_their_half_is_one_logical_link() -> None:
    """The regular case now that a save writes both halves: no relation is listed twice."""
    all_hosts = _hosts(
        board=[{"kind": "management", "direction": "parent", "host": "os1"}],
        os1=[{"kind": "management", "direction": "child", "host": "board"}],
    )

    resolved = resolve_all_relations(all_hosts)

    assert resolved[HostName("board")] == [
        ResolvedRelation(kind="management", direction="parent", host="os1", site="central")
    ]
    assert resolved[HostName("os1")] == [
        ResolvedRelation(kind="management", direction="child", host="board", site="central")
    ]


def test_two_halves_that_contradict_each_other_are_both_reported() -> None:
    """Only reachable by hand editing "hosts.mk" - a save re-states both halves. The resolver
    must not pick a winner: it does not know which side is the newer one, and dropping either
    would hide the mistake that validate_host_relations() reports."""
    all_hosts = _hosts(
        board=[{"kind": "management", "direction": "parent", "host": "os1"}],
        os1=[{"kind": "management", "direction": "parent", "host": "board"}],
    )

    resolved = resolve_all_relations(all_hosts)

    assert set(resolved[HostName("board")]) == {
        ResolvedRelation(kind="management", direction="parent", host="os1", site="central"),
        ResolvedRelation(kind="management", direction="child", host="os1", site="central"),
    }


def test_resolve_all_relations_skips_self_and_unknown_hosts() -> None:
    all_hosts = _hosts(
        board=[
            {"kind": "management", "direction": "parent", "host": "board"},
            {"kind": "management", "direction": "parent", "host": "ghost"},
            {"kind": "management", "direction": "parent", "host": "os1"},
        ],
        os1=None,
    )
    resolved = resolve_all_relations(all_hosts)
    assert resolved[HostName("board")] == [
        ResolvedRelation(kind="management", direction="parent", host="os1", site="central")
    ]
    assert HostName("ghost") not in resolved
