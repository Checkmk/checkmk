#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.utils.host_relations import RelationDirection, ResolvedRelation
from cmk.gui.watolib.host_relations import RelatedHost, resolve_all_relations
from tests.unit.cmk.gui.watolib.host_relations_fakes import fake_hosts, FakeHost


@pytest.mark.parametrize("stored, mirrored", [("child", "parent"), ("parent", "child")])
def test_one_stored_half_materializes_on_both_sides(
    stored: RelationDirection, mirrored: RelationDirection
) -> None:
    """A dialog row reads "this host is OS host of <other>", and so does the value the core
    gets - from either end, and for a half whose counterpart row was lost as well: the
    monitoring is never one-sided, only Setup can be."""
    resolved = resolve_all_relations(
        fake_hosts(srv=[{"kind": "management", "direction": stored, "host": "board"}], board=None)
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
        HostName("board"): FakeHost(
            "board", [{"kind": "management", "direction": "parent", "host": "os1"}]
        ),
        HostName("os1"): FakeHost("os1", site="remote"),
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
    all_hosts = fake_hosts(
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


def test_a_link_stored_twice_on_one_host_is_one_relation() -> None:
    """Saving a host with a repeated link is refused (see relation_conflicts), so this can only
    come from a hand written "hosts.mk" - the resolution must still not report it twice."""
    all_hosts = fake_hosts(
        board=[
            {"kind": "management", "direction": "parent", "host": "os1"},
            {"kind": "management", "direction": "parent", "host": "os1"},
        ],
        os1=None,
    )

    resolved = resolve_all_relations(all_hosts)

    assert resolved[HostName("board")] == [
        ResolvedRelation(kind="management", direction="parent", host="os1", site="central")
    ]


def test_two_halves_that_contradict_each_other_are_both_reported() -> None:
    """Only reachable by hand editing "hosts.mk" - a save re-states both halves. The resolver
    must not pick a winner: it does not know which side is the newer one, and dropping either
    would hide the mistake that validate_host_relations() reports."""
    all_hosts = fake_hosts(
        board=[{"kind": "management", "direction": "parent", "host": "os1"}],
        os1=[{"kind": "management", "direction": "parent", "host": "board"}],
    )

    resolved = resolve_all_relations(all_hosts)

    assert set(resolved[HostName("board")]) == {
        ResolvedRelation(kind="management", direction="parent", host="os1", site="central"),
        ResolvedRelation(kind="management", direction="child", host="os1", site="central"),
    }


@pytest.mark.parametrize(
    "relations, reason",
    [
        ([{"kind": "management", "direction": "child", "host": "board"}], "self-reference"),
        (
            [{"kind": "management", "direction": "child", "host": "ghost"}],
            "related host does not exist",
        ),
    ],
)
def test_every_dropped_relation_logs_a_reason(
    caplog: pytest.LogCaptureFixture, relations: object, reason: str
) -> None:
    with caplog.at_level(logging.DEBUG, logger="cmk.web.host_relations"):
        assert resolve_all_relations(fake_hosts(board=relations)) == {}

    assert reason in caplog.text


def test_an_end_this_version_does_not_know_logs_a_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A link written by a later version is skipped by the parser - silently, until here."""
    with caplog.at_level(logging.DEBUG, logger="cmk.web.host_relations"):
        assert (
            resolve_all_relations(
                fake_hosts(board=[{"kind": "management", "direction": "sideways", "host": "os1"}])
            )
            == {}
        )

    assert "sideways" in caplog.text
    assert "board" in caplog.text


def test_a_kind_this_version_does_not_know_logs_a_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The parser hands the link on - only the kinds this version knows can place it."""
    with caplog.at_level(logging.DEBUG, logger="cmk.web.host_relations"):
        assert (
            resolve_all_relations(
                fake_hosts(board=[{"kind": "peering", "direction": "symmetric", "host": "os1"}])
            )
            == {}
        )

    assert "peering" in caplog.text
    assert "board" in caplog.text


def test_a_malformed_stored_value_is_logged_as_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="cmk.web.host_relations"):
        assert resolve_all_relations(fake_hosts(board="not-a-list")) == {}

    assert "board" in caplog.text
    assert [record.levelno for record in caplog.records] == [logging.WARNING]


def test_resolve_all_relations_skips_self_and_unknown_hosts() -> None:
    all_hosts = fake_hosts(
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
