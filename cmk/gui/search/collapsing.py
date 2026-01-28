#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from itertools import groupby
from typing import Literal, Protocol

from cmk.gui.i18n import _
from cmk.shared_typing.unified_search import (
    ProviderName,
    UnifiedSearchResultCounts,
    UnifiedSearchResultItem,
    UnifiedSearchResultItemInlineButton,
)

type CollapsedResult = tuple[Sequence[UnifiedSearchResultItem], UnifiedSearchResultCounts]
type HostTopic = Literal["Hosts", "Host name", "Hostalias"]


class Collapser(Protocol):
    def __call__(
        self, results: Sequence[UnifiedSearchResultItem], counts: UnifiedSearchResultCounts
    ) -> CollapsedResult: ...


def get_collapser(*, provider: ProviderName | None, disabled: bool = False) -> Collapser:
    match (provider, disabled):
        case ProviderName.monitoring | None, False:
            return _collapse_items
        case _:
            return _collapse_none


def _collapse_none(
    results: Sequence[UnifiedSearchResultItem],
    counts: UnifiedSearchResultCounts,
) -> CollapsedResult:
    return results, counts


def _collapse_items(
    results: Sequence[UnifiedSearchResultItem],
    counts: UnifiedSearchResultCounts,
) -> CollapsedResult:
    collapsed_results: list[UnifiedSearchResultItem] = []
    collapsed_result_count = 0

    for _title, group in groupby(results, key=lambda item: item.title):
        host_items: dict[HostTopic, UnifiedSearchResultItem] = {}
        other_items: list[UnifiedSearchResultItem] = []

        # WARN: this logic only works because of some assumptions we make about the ordering from
        # the sort algorithm. We expect setup host, monitoring host, and optionaly monitoring host
        # alias to be grouped together in the unified search result. When that changes, then this
        # functionality will no longer work.
        for item in group:
            match item.topic:
                case "Hosts" | "Host name" | "Hostalias":
                    host_items.update({item.topic: item})
                case _:
                    other_items.append(item)

        match host_items:
            case {"Hosts": setup_item, "Host name": name, "Hostalias": alias}:
                collapsed_results.append(_collapse_host_items([name, alias], setup_item))
                collapsed_result_count += 1
            case {"Hosts": setup_item, "Host name": name}:
                collapsed_results.append(_collapse_host_items([name], setup_item))
            case {"Host name": name, "Hostalias": alias}:
                collapsed_results.append(_collapse_host_items([name, alias]))
                collapsed_result_count += 1
            case _:
                collapsed_results.extend(host_items.values())

        if other_items:
            collapsed_results.extend(other_items)

    updated_counts = UnifiedSearchResultCounts(
        total=len(collapsed_results),
        setup=counts.setup,
        monitoring=counts.monitoring - collapsed_result_count,
        customize=counts.customize,
    )

    return collapsed_results, updated_counts


def _collapse_host_items(
    monitoring_items: list[UnifiedSearchResultItem],
    setup_item: UnifiedSearchResultItem | None = None,
) -> UnifiedSearchResultItem:
    return UnifiedSearchResultItem(
        title=monitoring_items[0].title,
        target=monitoring_items[0].target,
        provider=ProviderName.monitoring,
        topic="Hosts",
        context=", ".join(item.topic for item in monitoring_items),
        inline_buttons=[
            UnifiedSearchResultItemInlineButton(
                target=setup_item.target,
                title=_("Edit"),
            )
        ]
        if setup_item
        else None,
    )
