#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from polyfactory.factories import DataclassFactory

from cmk.gui.search.sorting import get_sorter
from cmk.shared_typing.unified_search import (
    IconNames,
    ProviderName,
    SortType,
    UnifiedSearchResultItem,
    UnifiedSearchResultTarget,
)


class UnifiedSearchResultItemFactory(DataclassFactory[UnifiedSearchResultItem]):
    __check_model__ = False


def get_unsorted_results() -> list[UnifiedSearchResultItem]:
    return [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
    ]


def test_no_op_sorter() -> None:
    results = get_unsorted_results()
    get_sorter(None)(results)

    expected = [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
    ]

    assert results == expected


def test_alphabetical_sorter() -> None:
    results = get_unsorted_results()
    get_sorter(SortType.alphabetic)(results)

    expected = [
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
    ]

    assert results == expected


def test_weighted_sorter() -> None:
    results = get_unsorted_results()
    get_sorter(SortType.weighted_index, query="beta")(results)

    expected = [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Alpha",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Charlie",
            target=UnifiedSearchResultTarget(url="/charlie"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
    ]

    assert results == expected


def test_exact_match_in_parenthesis_ranks_higher_than_starts_with_query() -> None:
    results = [
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Alpha(bet)",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
    ]
    get_sorter(SortType.weighted_index, query="bet")(results)

    expected = [
        UnifiedSearchResultItem(
            title="Alpha(bet)",
            target=UnifiedSearchResultTarget(url="/alpha"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
        UnifiedSearchResultItem(
            title="Beta",
            target=UnifiedSearchResultTarget(url="/beta"),
            provider=ProviderName.setup,
            topic="Code",
            icon=IconNames.main_setup_active,
        ),
    ]

    assert results == expected


def test_weighted_sorter_takes_into_account_context() -> None:
    sample_result = UnifiedSearchResultItemFactory.build()
    results = [
        dataclasses.replace(sample_result, context="banana"),
        dataclasses.replace(sample_result, context="apple"),
        dataclasses.replace(sample_result, context="cookie"),
    ]
    get_sorter(SortType.weighted_index, query="beta")(results)

    value = [result.context for result in results]
    expected = ["apple", "banana", "cookie"]

    assert value == expected
