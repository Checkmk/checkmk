#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.gui.type_defs import SearchResult
from cmk.shared_typing.unified_search import (
    LoadingTransition,
    ProviderName,
    UnifiedSearchResultItem,
    UnifiedSearchResultTarget,
)

# TODO: drop this module when search engines are fully migrated.


def transform_legacy_results_to_unified(
    results: Iterable[SearchResult], topic: str, *, provider: ProviderName
) -> Iterable[UnifiedSearchResultItem]:
    return (
        UnifiedSearchResultItem(
            title=result.title,
            target=UnifiedSearchResultTarget(
                url=result.url,
                transition=transform_legacy_loading_transition_to_unified(
                    result.loading_transition
                ),
            ),
            topic=topic,
            provider=provider,
            context=result.context,
        )
        for result in results
    )


def transform_legacy_loading_transition_to_unified(
    transition: str | None,
) -> LoadingTransition | None:
    if transition is None:
        return None
    try:
        return LoadingTransition(transition)
    except ValueError:
        return None
