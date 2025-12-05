#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from polyfactory.factories import DataclassFactory

from cmk.gui.search.sorting import get_sorter
from cmk.shared_typing.unified_search import SortType, UnifiedSearchResultItem


class UnifiedSearchResultItemFactory(DataclassFactory[UnifiedSearchResultItem]):
    __check_model__ = False


def test_no_op_sorter() -> None:
    sample_result = UnifiedSearchResultItemFactory.build()
    results = [
        dataclasses.replace(sample_result, title="Charlie"),
        dataclasses.replace(sample_result, title="Beta"),
        dataclasses.replace(sample_result, title="Alpha"),
    ]
    get_sorter(None)(results)

    value = [result.title for result in results]
    expected = ["Charlie", "Beta", "Alpha"]

    assert value == expected


def test_alphabetical_sorter() -> None:
    sample_result = UnifiedSearchResultItemFactory.build()
    results = [
        dataclasses.replace(sample_result, title="Charlie"),
        dataclasses.replace(sample_result, title="Beta"),
        dataclasses.replace(sample_result, title="Alpha"),
    ]
    get_sorter(SortType.alphabetic)(results)

    value = [result.title for result in results]
    expected = ["Alpha", "Beta", "Charlie"]

    assert value == expected


def test_weighted_sorter() -> None:
    sample_result = UnifiedSearchResultItemFactory.build()
    results = [
        dataclasses.replace(sample_result, title="Charlie"),
        dataclasses.replace(sample_result, title="Beta"),
        dataclasses.replace(sample_result, title="Alpha"),
    ]
    get_sorter(SortType.weighted_index, query="beta")(results)

    value = [result.title for result in results]
    expected = ["Beta", "Alpha", "Charlie"]

    assert value == expected


def test_exact_match_in_parenthesis_ranks_higher_than_starts_with_query() -> None:
    sample_result = UnifiedSearchResultItemFactory.build()
    results = [
        dataclasses.replace(sample_result, title="Beta"),
        dataclasses.replace(sample_result, title="Alpha(bet)"),
    ]
    get_sorter(SortType.weighted_index, query="bet")(results)

    value = [result.title for result in results]
    expected = ["Alpha(bet)", "Beta"]

    assert value == expected


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
