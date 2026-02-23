#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools

from cmk.gui.search.sorting import get_sorter
from cmk.shared_typing.unified_search import (
    ProviderName,
    SortType,
    UnifiedSearchResultItem,
    UnifiedSearchResultTarget,
)

I = functools.partial(
    UnifiedSearchResultItem,
    target=UnifiedSearchResultTarget(url=""),
    provider=ProviderName.setup,
)


def get_results_alphabetically() -> list[UnifiedSearchResultItem]:
    return [
        I(title="Azure AD Connect", topic="Service monitoring rules"),
        I(title="Azure AD Connect (deprecated)", topic="Service monitoring rules"),
        I(title="Azure App Registration", topic="Service monitoring rules"),
        I(title="Azure Load Balancer Health", topic="Service monitoring rules"),
        I(title="Azure Load Balancer Health (deprecated)", topic="Service monitoring rules"),
        I(title="Azure DB Storage", topic="Service monitoring rules"),
        I(title="Azure DB Storage (deprecated)", topic="Service monitoring rules"),
    ]


def test_weighted_index_sorting_with_azure_query() -> None:
    results = get_results_alphabetically()
    get_sorter(SortType.weighted_index, query="azure")(results)

    value = [(result.title, result.topic) for result in results]
    expected = [
        ("Azure AD Connect", "Service monitoring rules"),
        ("Azure App Registration", "Service monitoring rules"),
        ("Azure DB Storage", "Service monitoring rules"),
        ("Azure Load Balancer Health", "Service monitoring rules"),
        ("Azure AD Connect (deprecated)", "Service monitoring rules"),
        ("Azure DB Storage (deprecated)", "Service monitoring rules"),
        ("Azure Load Balancer Health (deprecated)", "Service monitoring rules"),
    ]

    assert value == expected
