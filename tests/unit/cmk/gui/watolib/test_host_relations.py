#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.utils.host_relation_kinds import RELATION_KINDS
from cmk.gui.utils.host_relations import (
    RelationDirection,
    RelationLink,
    RelationsValue,
    ResolvedRelation,
    reverse_direction,
)
from cmk.gui.watolib.host_relations import (
    host_relations_form_spec,
    RelatedHost,
    relation_conflicts,
    RelationConflict,
    relations_deletion_note,
    relations_or_user_error,
    resolve_all_relations,
)
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from tests.unit.cmk.gui.watolib.host_relations_fakes import fake_hosts, FakeHost

_VISITOR_OPTIONS = VisitorOptions(migrate_values=False, mask_values=False)


def test_the_form_offers_every_end_of_every_kind_in_one_row() -> None:
    spec, _value = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS).to_vue(DEFAULT_VALUE)
    assert isinstance(spec, shared_type_defs.List)
    row = spec.element_template
    assert isinstance(row, shared_type_defs.CascadingSingleChoice)
    assert row.layout == shared_type_defs.CascadingSingleChoiceLayout.horizontal
    assert [element.name for element in row.elements] == [
        f"{kind.id}_{direction}"
        for kind in RELATION_KINDS.values()
        for direction in kind.directions()
    ]


def test_the_form_offers_both_ends_of_the_management_relation() -> None:
    """Pinned separately: the names above are derived, these are what the dialog submits."""
    spec, _value = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS).to_vue(DEFAULT_VALUE)
    assert isinstance(spec, shared_type_defs.List)
    row = spec.element_template
    assert isinstance(row, shared_type_defs.CascadingSingleChoice)
    assert [element.name for element in row.elements] == [
        "management_parent",
        "management_child",
    ]


def test_the_form_titles_read_as_a_sentence_about_the_host_being_edited() -> None:
    spec, _value = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS).to_vue(DEFAULT_VALUE)
    assert isinstance(spec, shared_type_defs.List)
    row = spec.element_template
    assert isinstance(row, shared_type_defs.CascadingSingleChoice)
    assert [element.title for element in row.elements] == [
        "is management board of",
        "is OS host of",
    ]


def test_the_form_round_trips_stored_links() -> None:
    links: RelationsValue = [
        {"kind": "management", "direction": "parent", "host": HostName("mgmt1")},
        {"kind": "management", "direction": "child", "host": HostName("os1")},
    ]
    visitor = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS)
    assert visitor.validate(RawDiskData(links)) == []
    assert visitor.to_disk(RawDiskData(links)) == links


def test_the_form_leaves_out_a_link_it_cannot_offer_a_row_for() -> None:
    """A kind of a later version has no element to select, so the dialog cannot show its row."""
    links: RelationsValue = [
        {"kind": "peering", "direction": "symmetric", "host": HostName("peer")},
        {"kind": "management", "direction": "child", "host": HostName("os1")},
    ]
    visitor = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS)

    assert visitor.to_disk(RawDiskData(links)) == [
        {"kind": "management", "direction": "child", "host": HostName("os1")}
    ]


def test_the_form_stores_the_rows_the_dialog_submits() -> None:
    """The dialog sends the (relation type, host name) pairs the cascading choice produces."""
    rows = RawFrontendData([["management_parent", "mgmt1"], ["management_child", "os1"]])
    visitor = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS)
    assert visitor.validate(rows) == []
    assert visitor.to_disk(rows) == [
        {"kind": "management", "direction": "parent", "host": "mgmt1"},
        {"kind": "management", "direction": "child", "host": "os1"},
    ]


def test_the_form_asks_for_a_host_the_row_is_missing() -> None:
    """The dialog submits the empty name the choice defaults to."""
    visitor = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS)
    messages = visitor.validate(RawFrontendData([["management_child", ""]]))
    assert [message.message for message in messages] == ["Select the host this relation points to."]


def test_the_form_rejects_a_host_name_that_cannot_be_stored() -> None:
    visitor = get_visitor(host_relations_form_spec(), _VISITOR_OPTIONS)
    messages = visitor.validate(RawFrontendData([["management_child", "no spaces"]]))
    assert [message.message for message in messages] == ["This is not a usable host name."]


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


def test_relations_deletion_note_counts_the_related_hosts() -> None:
    host = FakeHost(
        "mgmt",
        [
            {"kind": "management", "direction": "child", "host": "h1"},
            {"kind": "management", "direction": "child", "host": "h2"},
        ],
    )
    assert relations_deletion_note(host) == (
        "This host has related hosts: 2<br>"
        "The relations of this host will be deleted, and removed from the related hosts "
        "wherever they can be written."
    )


def test_relations_deletion_note_counts_each_related_host_once() -> None:
    host = FakeHost(
        "mgmt",
        [
            {"kind": "management", "direction": "child", "host": "h1"},
            {"kind": "management", "direction": "parent", "host": "h1"},
        ],
    )
    note = relations_deletion_note(host)
    assert note is not None
    assert note.startswith("This host has related hosts: 1")


@pytest.mark.parametrize("relations", [None, [], "not a list"])
def test_relations_deletion_note_is_absent_without_own_relations(relations: object) -> None:
    assert relations_deletion_note(FakeHost("h1", relations)) is None


@pytest.mark.parametrize(
    "links",
    [
        pytest.param(
            [{"kind": "management", "direction": "parent", "host": HostName("mgmt1")}],
            id="a sound link",
        ),
        pytest.param(
            [{"kind": "management", "direction": "parent", "host": HostName("ghost")}],
            id="a host that is not there - reported by validate_host_relations(), not refused",
        ),
        pytest.param(
            [
                {"kind": "management", "direction": "parent", "host": HostName("mgmt1")},
                {"kind": "management", "direction": "parent", "host": HostName("mgmt2")},
            ],
            id="the same end towards two hosts",
        ),
        pytest.param(
            [
                {"kind": "management", "direction": "parent", "host": HostName("mgmt1")},
                {"kind": "peering", "direction": "symmetric", "host": HostName("mgmt1")},
            ],
            id="two relations of different kinds towards the same host",
        ),
        pytest.param(
            [
                {"kind": "peering", "direction": "parent", "host": HostName("mgmt1")},
                {"kind": "peering", "direction": "child", "host": HostName("mgmt1")},
            ],
            id="a relation of a later version is not this one's to judge",
        ),
    ],
)
def test_relation_conflicts_accepts(links: Sequence[RelationLink]) -> None:
    assert relation_conflicts(links, HostName("srv1")) == []


def test_a_link_of_a_later_version_to_this_host_itself_is_still_refused() -> None:
    """Wrong whatever the relation means - and the only thing that can be said about it."""
    assert relation_conflicts(
        [{"kind": "peering", "direction": "symmetric", "host": HostName("srv1")}],
        HostName("srv1"),
    ) == [RelationConflict(reason="self_link")]


@pytest.mark.parametrize(
    "links, expected",
    [
        pytest.param(
            [{"kind": "management", "direction": "parent", "host": HostName("srv1")}],
            RelationConflict(reason="self_link"),
            id="self link",
        ),
        pytest.param(
            [
                {"kind": "management", "direction": "parent", "host": HostName("mgmt1")},
                {"kind": "management", "direction": "child", "host": HostName("mgmt1")},
            ],
            RelationConflict(
                reason="contradicting_directions",
                host=HostName("mgmt1"),
                kind_id="management",
            ),
            id="both ends",
        ),
        pytest.param(
            [
                {"kind": "management", "direction": "parent", "host": HostName("mgmt1")},
                {"kind": "management", "direction": "parent", "host": HostName("mgmt1")},
            ],
            RelationConflict(reason="duplicate", host=HostName("mgmt1"), kind_id="management"),
            id="duplicate",
        ),
    ],
)
def test_relation_conflicts_reports(
    links: Sequence[RelationLink], expected: RelationConflict
) -> None:
    assert relation_conflicts(links, HostName("srv1"))[0] == expected


def test_a_contradiction_names_both_ends_of_the_relation() -> None:
    conflicts = relation_conflicts(
        [
            {"kind": "management", "direction": "parent", "host": HostName("other")},
            {"kind": "management", "direction": "child", "host": HostName("other")},
        ],
        HostName("srv1"),
    )

    assert conflicts[0].message() == (
        "This host is linked to 'other' both as its 'Management board' and as its 'OS host'. "
        "A host can only sit at one end of a relation."
    )


@pytest.mark.parametrize(
    "kind_id, direction",
    [
        (kind.id, direction)
        for kind in RELATION_KINDS.values()
        for direction in kind.directions()
        if direction != "symmetric"
    ],
)
def test_every_relation_can_say_what_it_contradicts(
    kind_id: str, direction: RelationDirection
) -> None:
    """An end the report cannot name would only show up as a crash."""
    conflicts = relation_conflicts(
        [
            {"kind": kind_id, "direction": direction, "host": HostName("other")},
            {"kind": kind_id, "direction": reverse_direction(direction), "host": HostName("other")},
        ],
        HostName("srv1"),
    )

    assert "other" in conflicts[0].message()


def test_relations_or_user_error_reports_a_malformed_value() -> None:
    with pytest.raises(MKUserError, match="malformed"):
        relations_or_user_error("not-a-list")
