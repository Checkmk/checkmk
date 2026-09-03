#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The two host relation formats: what Setup stores, and what one side writes for the other."""

import json
from typing import get_args

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.utils.host_relations import (
    dump_resolved_relations,
    parse_relations_value,
    parse_resolved_relations,
    referenced_host_names,
    relation_key,
    RelationDirection,
    RELATIONS_CUSTOM_VARIABLE,
    RELATIONS_MACRO,
    relations_or_empty,
    ResolvedRelation,
    reverse_direction,
)


def test_livestatus_reports_the_macro_without_its_underscore() -> None:
    assert RELATIONS_MACRO == "_RELATIONS"
    assert RELATIONS_CUSTOM_VARIABLE == "RELATIONS"


def test_what_is_written_is_what_is_read() -> None:
    """The one thing nothing else can check: Setup writes this, a site's core hands it back.

    Order included - the host details render one card per relation, so the codec must not
    reshuffle them.
    """
    relations = [
        ResolvedRelation(kind="management", direction="parent", host="board", site="central"),
        ResolvedRelation(kind="management", direction="child", host="os1", site="remote"),
    ]

    assert list(parse_resolved_relations(dump_resolved_relations(relations))) == relations


def test_no_relations_are_written_as_an_empty_list() -> None:
    assert list(parse_resolved_relations(dump_resolved_relations([]))) == []


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(None, id="host without the macro"),
        pytest.param("", id="empty value"),
        pytest.param("not json", id="not json at all"),
        pytest.param('{"kind": "management", "direction": "child"}', id="not a list"),
        pytest.param('["junk"]', id="entry is not a mapping"),
        pytest.param(
            '[{"kind": "management", "direction": "nonsense", "host": "a", "site": "central"}]',
            id="unknown direction",
        ),
        pytest.param(
            '[{"direction": "child", "host": "a", "site": "central"}]',
            id="no kind",
        ),
        pytest.param(
            '[{"kind": "", "direction": "child", "host": "a", "site": "central"}]',
            id="empty kind",
        ),
        pytest.param(
            '[{"kind": "management", "direction": "child", "site": "central"}]', id="no host"
        ),
        pytest.param('[{"kind": "management", "direction": "child", "host": "a"}]', id="no site"),
        pytest.param(
            '[{"kind": "management", "direction": "child", "host": ["a"], "site": "central"}]',
            id="host list",
        ),
        # An unhashable direction used to raise TypeError out of the membership check, which no
        # caller guards against.
        pytest.param(
            '[{"kind": "management", "direction": ["child"], "host": "a", "site": "c"}]',
            id="direction list",
        ),
        pytest.param(
            '[{"kind": "management", "direction": {}, "host": "a", "site": "c"}]',
            id="direction mapping",
        ),
        pytest.param(
            '[{"kind": ["management"], "direction": "child", "host": "a", "site": "c"}]',
            id="kind list",
        ),
        pytest.param(
            '[{"kind": "management", "direction": "child", "host": "", "site": "c"}]',
            id="empty host",
        ),
        pytest.param(
            '[{"kind": "management", "direction": "child", "host": "a", "site": ""}]',
            id="empty site",
        ),
    ],
)
def test_nothing_a_reader_cannot_use_is_yielded(raw: str | None) -> None:
    """A value a reader did not write must never break the page showing it."""
    assert list(parse_resolved_relations(raw)) == []


def test_a_kind_this_version_does_not_know_is_still_yielded() -> None:
    """Which kinds exist is not this module's question - see host_relation_kinds."""
    raw = json.dumps(
        [{"kind": "peering", "direction": "symmetric", "host": "os2", "site": "remote"}]
    )

    assert list(parse_resolved_relations(raw)) == [
        ResolvedRelation(kind="peering", direction="symmetric", host="os2", site="remote")
    ]


def test_usable_entries_survive_an_unusable_one() -> None:
    raw = json.dumps(
        [
            {"kind": "management", "direction": "child", "host": "os1", "site": "remote"},
            {"kind": "management", "direction": "nonsense", "host": "os2", "site": "remote"},
        ]
    )

    assert list(parse_resolved_relations(raw)) == [
        ResolvedRelation(kind="management", direction="child", host="os1", site="remote")
    ]


def test_the_two_ends_of_a_relation_answer_each_other() -> None:
    assert reverse_direction("parent") == "child"
    assert reverse_direction("child") == "parent"
    for direction in get_args(RelationDirection):
        assert reverse_direction(reverse_direction(direction)) == direction


def test_a_symmetric_relation_reads_the_same_from_either_side() -> None:
    assert reverse_direction("symmetric") == "symmetric"


def test_the_stored_direction_names_are_what_is_on_disk() -> None:
    """Pinned so that renaming one has to be a deliberate act.

    These strings are in every "hosts.mk" and in every core configuration that already holds a
    relation. The dialog's titles and the labels the monitoring shows live elsewhere precisely so
    that a wording change stops there - if a change to one of them reaches this test, it is
    changing stored data and needs a migration, not a rename.
    """
    assert set(get_args(RelationDirection)) == {"parent", "child", "symmetric"}


def test_a_stored_link_keeps_its_ends_and_gets_a_real_host_name() -> None:
    links = parse_relations_value([{"kind": "management", "direction": "child", "host": "os1"}])

    assert links == [{"kind": "management", "direction": "child", "host": "os1"}]
    assert isinstance(links[0]["host"], HostName)


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("not a list", id="not a list"),
        pytest.param(["junk"], id="entry is not a mapping"),
        pytest.param([{"direction": "child", "host": "os1"}], id="no kind"),
        pytest.param([{"kind": "", "direction": "child", "host": "os1"}], id="empty kind"),
        pytest.param(
            [{"kind": ["management"], "direction": "child", "host": "os1"}], id="kind list"
        ),
        pytest.param([{"kind": "management", "host": "os1"}], id="no direction"),
        pytest.param(
            [{"kind": "management", "direction": ["child"], "host": "os1"}], id="direction list"
        ),
        pytest.param([{"kind": "management", "direction": "child"}], id="no host"),
        pytest.param([{"kind": "management", "direction": "child", "host": ""}], id="empty host"),
        pytest.param(
            [{"kind": "management", "direction": "child", "host": 1}], id="host not a string"
        ),
        # An unusable name is what every later reader of the link would trip over, so it is a
        # structural defect like any other - and a ValueError, not a HostNameValidationError
        # escaping to a crash report.
        pytest.param(
            [{"kind": "management", "direction": "child", "host": "no spaces allowed"}],
            id="invalid host name",
        ),
    ],
)
def test_a_link_that_cannot_be_used_is_a_value_error(raw: object) -> None:
    with pytest.raises(ValueError):
        parse_relations_value(raw)

    assert relations_or_empty(raw) == []


def test_an_end_this_version_does_not_know_costs_only_its_own_row() -> None:
    """A later version can add one, and whatever reads the attribute writes back what it parsed.

    Raising for the whole list - as an unusable value does - would turn one unknown row into a
    host without any relations at all the next time it is saved.
    """
    links = parse_relations_value(
        [
            {"kind": "management", "direction": "child", "host": "os1"},
            {"kind": "backup", "direction": "sideways", "host": "backup"},
            {"kind": "management", "direction": "parent", "host": "board"},
        ]
    )

    assert links == [
        {"kind": "management", "direction": "child", "host": "os1"},
        {"kind": "management", "direction": "parent", "host": "board"},
    ]


def test_an_unknown_end_is_skipped_before_the_host_name_is_read() -> None:
    """A row of a later version must not fail on a field this version happens to read strictly."""
    assert (
        parse_relations_value([{"kind": "management", "direction": "sideways", "host": ""}]) == []
    )


def test_an_unknown_end_is_reported_to_whoever_wants_to_know() -> None:
    reported: list[str] = []

    parse_relations_value(
        [{"kind": "management", "direction": "sideways", "host": "os1"}],
        on_unknown_direction=reported.append,
    )

    assert reported == ["sideways"]


def test_a_kind_this_version_does_not_know_is_still_parsed() -> None:
    """Whether a kind exists is host_relation_kinds' question, not the wire format's."""
    assert parse_relations_value(
        [{"kind": "peering", "direction": "symmetric", "host": "os1"}]
    ) == [{"kind": "peering", "direction": "symmetric", "host": "os1"}]


def test_referenced_host_names_are_the_linked_hosts() -> None:
    links = parse_relations_value(
        [
            {"kind": "management", "direction": "child", "host": "os1"},
            {"kind": "management", "direction": "parent", "host": "board"},
            {"kind": "management", "direction": "child", "host": "os1"},
        ]
    )

    assert referenced_host_names(links) == {HostName("os1"), HostName("board")}


def test_a_link_is_identified_by_its_kind_its_end_and_its_host() -> None:
    links = parse_relations_value(
        [
            {"kind": "management", "direction": "child", "host": "os1"},
            {"kind": "management", "direction": "parent", "host": "os1"},
            {"kind": "peering", "direction": "symmetric", "host": "os1"},
        ]
    )

    assert len({relation_key(link) for link in links}) == 3
    assert relation_key(links[0]) == ("management", "child", HostName("os1"))
