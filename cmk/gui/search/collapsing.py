#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import groupby
from typing import Final, Protocol

from cmk.gui.i18n import _
from cmk.shared_typing.unified_search import (
    ProviderName,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
    UnifiedSearchResultItemInlineButton,
)

type CollapsedResult = tuple[list[UnifiedSearchResultItem], UnifiedSearchResultCounts]

_EDIT_TITLE: Final = _("Edit")
_HOST_TOPIC_TITLE: Final = "Hosts"


class Collapser(Protocol):
    def __call__(
        self, results: list[UnifiedSearchResultItem], counts: UnifiedSearchResultCounts
    ) -> CollapsedResult: ...


def get_collapser(*, provider: ProviderName | None, disabled: bool = False) -> Collapser:
    match (provider, disabled):
        case ProviderName.monitoring | None, False:
            return _collapse_items
        case _:
            return _collapse_none


def _collapse_none(
    results: list[UnifiedSearchResultItem],
    counts: UnifiedSearchResultCounts,
) -> CollapsedResult:
    return results, counts


def _collapse_items(
    results: list[UnifiedSearchResultItem],
    counts: UnifiedSearchResultCounts,
) -> CollapsedResult:
    collapsed_results: list[UnifiedSearchResultItem] = []

    for title, group in groupby(results, key=lambda item: item.title):
        host_items = []
        other_items = []

        # WARN: this logic only works because of some assumptions we make about the ordering from
        # the sort algorithm. We expect setup host, monitoring host, and optionaly monitoring host
        # alias to be grouped together in the unified search result. When that changes, then this
        # functionality will no longer work.
        for item in group:
            match item.topic:
                case "Hosts" | "Host name":
                    host_items.append(item)
                case "Hostalias" if host_items:
                    host_items.append(item)
                case _:
                    other_items.append(item)

        if len(host_items) >= 2:
            collapsed_results.append(_collapse_host_items(host_items))
            counts.monitoring -= len(host_items) - 2

        if other_items:
            collapsed_results.extend(other_items)

    # update counts to reflect the state when results have been collapsed.
    counts.total = len(collapsed_results)

    return collapsed_results, counts


def _collapse_host_items(host_items: list[UnifiedSearchResultItem]) -> UnifiedSearchResultItem:
    setup_item, *monitoring_items = host_items

    return UnifiedSearchResultItem(
        title=setup_item.title,
        target=monitoring_items[0].target,
        provider=ProviderName.monitoring,
        topic=_HOST_TOPIC_TITLE,
        context=", ".join(item.topic for item in monitoring_items),
        inline_buttons=[
            UnifiedSearchResultItemInlineButton(
                target=setup_item.target,
                title=_EDIT_TITLE,
            )
        ],
    )
