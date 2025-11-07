#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.search.sorting import get_sorter
from cmk.gui.search.type_defs import UnifiedSearchResultItem, UnifiedSearchResultTarget


def get_unsorted_results() -> list[UnifiedSearchResultItem]:
    return [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider="setup",
            topic="Code",
            icon="",
        ),
    ]


def test_no_op_sorter() -> None:
    results = get_unsorted_results()
    get_sorter(None)(results)

    expected = [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider="setup",
            topic="Code",
            icon="",
        ),
    ]

    assert results == expected


def test_alphabetical_sorter() -> None:
    results = get_unsorted_results()
    get_sorter("alphabetic")(results)

    expected = [
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider="setup",
            topic="Code",
            icon="",
        ),
    ]

    assert results == expected


def test_weighted_sorter() -> None:
    results = get_unsorted_results()
    get_sorter("weighted_index", query="beta")(results)

    expected = [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider="setup",
            topic="Code",
            icon="",
        ),
    ]

    assert results == expected


def test_exact_match_in_parenthesis_ranks_higher_than_starts_with_query() -> None:
    results = [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Alpha(bet)",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider="setup",
            topic="Code",
            icon="",
        ),
    ]
    get_sorter("weighted_index", query="bet")(results)

    expected = [
        UnifiedSearchResultItem(
            title="Alpha(bet)",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider="setup",
            topic="Code",
            icon="",
        ),
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider="setup",
            topic="Code",
            icon="",
        ),
    ]

    assert results == expected
