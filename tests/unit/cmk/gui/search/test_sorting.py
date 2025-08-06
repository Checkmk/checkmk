#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.search.sorting import get_sorter
from cmk.gui.search.type_defs import UnifiedSearchResultItem


def get_unsorted_results() -> list[UnifiedSearchResultItem]:
    return [
        UnifiedSearchResultItem(title="Beta", url="/beta", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Charlie", url="/charlie", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Alpha", url="/alpha", provider="setup", topic="Code"),
    ]


def test_no_op_sorter() -> None:
    results = get_unsorted_results()
    sorter = get_sorter(None)
    sorter(results)

    expected = [
        UnifiedSearchResultItem(title="Beta", url="/beta", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Charlie", url="/charlie", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Alpha", url="/alpha", provider="setup", topic="Code"),
    ]

    assert results == expected


def test_alphabetical_sorter() -> None:
    results = get_unsorted_results()
    sorter = get_sorter("alphabetic")
    sorter(results)

    expected = [
        UnifiedSearchResultItem(title="Alpha", url="/alpha", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Beta", url="/beta", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Charlie", url="/charlie", provider="setup", topic="Code"),
    ]

    assert results == expected


def test_weighted_sorter() -> None:
    results = get_unsorted_results()
    sorter = get_sorter("weighted_index", query="bet")
    sorter(results)

    expected = [
        UnifiedSearchResultItem(title="Beta", url="/beta", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Alpha", url="/alpha", provider="setup", topic="Code"),
        UnifiedSearchResultItem(title="Charlie", url="/charlie", provider="setup", topic="Code"),
    ]

    assert results == expected
