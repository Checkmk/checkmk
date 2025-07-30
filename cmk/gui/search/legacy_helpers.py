#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.gui.search.type_defs import Provider, UnifiedSearchResultItem
from cmk.gui.type_defs import SearchResult

# TODO: drop this module when search engines are fully migrated.


def transform_legacy_results_to_unified(
    results: Iterable[SearchResult], topic: str, *, provider: Provider
) -> Iterable[UnifiedSearchResultItem]:
    return (
        UnifiedSearchResultItem(
            title=result.title,
            url=result.url,
            topic=topic,
            provider=provider,
            context=result.context,
        )
        for result in results
    )
