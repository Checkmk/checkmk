#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon Livestatus-filter validation (cmk.maps.shared.filters)."""

import pytest

from cmk.maps.shared.filters import (
    excluded_members_filter,
    ExcludedMembers,
    FILTER_NESTING_MAX,
    normalize_object_filter,
    validate_member_pattern,
)


def test_appends_trailing_newline() -> None:
    # NagVis stores single-filter dyngroups without a trailing separator.
    assert normalize_object_filter("Filter: host_name ~ ^web") == "Filter: host_name ~ ^web\n"


def test_expands_literal_backslash_n() -> None:
    assert normalize_object_filter("Filter: a\\nFilter: b") == "Filter: a\nFilter: b\n"


def test_keeps_a_literal_backslash_r_inside_one_line() -> None:
    # Only ``\n`` is un-escaped (NagVis' own separator). A literal backslash-r is
    # two harmless characters for Livestatus, so it must not be mistaken for a CR
    # and split a line apart.
    assert normalize_object_filter("Filter: a\\rb") == "Filter: a\\rb\n"


def test_rejects_control_characters() -> None:
    # A NUL survives both splitlines() and the ``.*`` of the header regex, so it
    # would otherwise reach Livestatus inside an otherwise well-formed line.
    with pytest.raises(ValueError):
        normalize_object_filter("Filter: a\x00Stats: state = 0")


def test_accepts_combinator_headers() -> None:
    assert (
        normalize_object_filter("Filter: a\\nFilter: b\\nOr: 2") == "Filter: a\nFilter: b\nOr: 2\n"
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("Filter: a\\nNegate:", "Filter: a\nNegate:\n", id="negate"),
        pytest.param("Filter: a\\nNegate: 1", "Filter: a\nNegate:\n", id="negate-argument"),
        pytest.param("Filter:a\\nFilter:b\\nOr:2", "Filter: a\nFilter: b\nOr: 2\n", id="no-space"),
    ],
)
def test_accepts_filters_as_livestatus_reads_them(value: str, expected: str) -> None:
    assert normalize_object_filter(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("Filter: a\\nStats: state = 0", id="stats"),
        pytest.param("Filter: a\\nColumns: name address", id="columns"),
        pytest.param("Filter: a\\nOutputFormat: python", id="outputformat"),
        pytest.param("Filter: a\\nGET hosts", id="get"),
        pytest.param("Filter: a\\nAuthUser: admin", id="authuser"),
        # Livestatus splits headers on newlines, and str.splitlines() splits on
        # more than \n — every one of those separators must be seen, or a smuggled
        # header would ride inside what looks like a single Filter: line.
        pytest.param("Filter: a\rStats: state = 0", id="carriage-return"),
        pytest.param("Filter: a\r\nStats: state = 0", id="crlf"),
        pytest.param("Filter: a\u2028Stats: state = 0", id="line-separator"),
        pytest.param("Filter: a\x0bStats: state = 0", id="vertical-tab"),
        pytest.param("Filter: a\x0cStats: state = 0", id="form-feed"),
        pytest.param("Filter: a\x1cStats: state = 0", id="file-separator"),
        pytest.param("Stats: state = 0", id="bare-stats"),
        pytest.param("GET hosts", id="bare-get"),
        pytest.param("Filter:", id="filter-without-argument"),
        pytest.param("Filter: a\\nOr:", id="or-without-count"),
        pytest.param("Filter: a\\nFilter: b\\nOr: two", id="or-without-a-number"),
        pytest.param("Filter: a\\nFilter: b\\nOr: ²", id="or-with-a-non-ascii-digit"),
        pytest.param("filter: name = a", id="lowercase"),
        pytest.param("", id="empty"),
    ],
)
def test_rejects_injected_headers(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_object_filter(value)


def _alternating(levels: int) -> str:
    return "Filter: a\n" + "".join(
        f"Filter: b\n{'Or' if i % 2 else 'And'}: 2\n" for i in range(levels)
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(_alternating(FILTER_NESTING_MAX), id="alternating-to-the-limit"),
        pytest.param("Filter: a\n" + "Filter: b\nOr: 2\n" * 500, id="one-operator-merges"),
        pytest.param("".join(f"Filter: a{i}\n" for i in range(500)) + "Or: 500", id="flat"),
    ],
)
def test_accepts_a_filter_livestatus_runs_quickly(value: str) -> None:
    normalize_object_filter(value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(_alternating(FILTER_NESTING_MAX + 1), id="alternating"),
        pytest.param("Filter: a\n" + "Filter: b\nAnd: 2\nNegate:\n" * 4, id="negate-adds-a-level"),
    ],
)
def test_rejects_a_filter_nested_deeper_than_livestatus_runs_quickly(value: str) -> None:
    with pytest.raises(ValueError, match="deeper"):
        normalize_object_filter(value)


def test_member_pattern_is_trimmed() -> None:
    assert validate_member_pattern("  ^test-  ") == "^test-"


@pytest.mark.parametrize("pattern", ["", "   ", "x" * 1025])
def test_member_pattern_rejects_empty_and_overlong(pattern: str) -> None:
    with pytest.raises(ValueError):
        validate_member_pattern(pattern)


@pytest.mark.parametrize(
    "members, pattern, expected",
    [
        pytest.param("host_services", "^CPU", "Filter: description !~~ ^CPU\n", id="host"),
        pytest.param("host_services", "h1~~^CPU", "", id="host-ignores-service-pattern"),
        pytest.param("hosts", "^test-", "Filter: name !~~ ^test-\n", id="group-hosts"),
        pytest.param("hosts", "^test-~~^CPU", "", id="group-hosts-ignore-service-pattern"),
        pytest.param("services", "^test-", "Filter: host_name !~~ ^test-\n", id="group-services"),
        pytest.param(
            "services",
            "^test-~~^CPU~~ignored",
            "Filter: host_name !~~ ^test-\nFilter: description !~~ ^CPU\nOr: 2\n",
            id="nagvis-reads-two-parts",
        ),
        pytest.param(
            "services", "~~^CPU", "Filter: description !~~ ^CPU\n", id="any-host-of-the-group"
        ),
    ],
)
def test_excluded_members_filter_builds_what_nagvis_does(
    members: ExcludedMembers, pattern: str, expected: str
) -> None:
    assert excluded_members_filter(members, pattern) == expected
