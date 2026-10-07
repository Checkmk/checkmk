#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import asdict
from typing import Final, override

from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.shared_typing.unified_search import (
    MessageVariant,
    ProviderName,
    SortType,
    UnifiedSearchApiResponse,
    UnifiedSearchApiResponseMessage,
    UnifiedSearchResultCounts,
)

from ._collapsing import get_collapser
from ._engines._livestatus import LivestatusSearchEngine
from ._engines._redis import RedisSearchEngine
from ._unified import UnifiedSearch
from .permissions import (
    category_permissions_handler_registry,
    search_permissions_handler_registry,
)

# Before making this something configurable, we want to first hardcode this setting to a reasonable
# value and get feedback from users.
_LIVESTATUS_ENGINE_ROW_LIMIT: Final = 500

# Deliberately independent of the user-configurable `config.quicksearch_search_order`, which drives
# the legacy sidebar quicksearch snapin instead.
_UNIFIED_SEARCH_LIVESTATUS_ORDER: Final[list[tuple[str, str]]] = [
    ("menu", "continue"),
    ("h", "continue"),
    ("al", "continue"),
    ("ad", "continue"),
    ("s", "continue"),
]


class PageUnifiedSearch(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        query = ctx.request.get_str_input_mandatory("q")
        provider = self._parse_provider_query_param(ctx.request)
        sort_type = self._parse_sort_query_param(ctx.request)
        collapser_disabled = self._parse_disabled_collapser(ctx.request)

        unified_search_engine = UnifiedSearch(
            redis_engine=RedisSearchEngine(
                ctx.config,
                {
                    entry.provider: entry.build(ctx)
                    for entry in search_permissions_handler_registry.values()
                },
                category_permission_handlers={
                    entry.category: entry.build(ctx)
                    for entry in category_permissions_handler_registry.values()
                },
            ),
            livestatus_engine=LivestatusSearchEngine(
                ctx.config,
                ctx.request,
                row_limit=_LIVESTATUS_ENGINE_ROW_LIMIT,
                search_order=_UNIFIED_SEARCH_LIVESTATUS_ORDER,
            ),
        )

        result = unified_search_engine.search(
            query,
            provider=provider,
            sort_type=sort_type,
        )

        collapse = get_collapser(provider=provider, disabled=collapser_disabled)
        search_results, search_count = collapse(result.results, result.counts)
        # NOTE: checking the original counts instead of the collapsed counts because the result
        # limiting occurs inside the livestatus engine, not during post-processing.
        messages = self._collect_api_response_messages(result.counts)

        return asdict(
            UnifiedSearchApiResponse(
                url=ctx.request.url,
                query=query,
                counts=search_count,
                results=search_results,
                messages=messages,
            )
        )

    def _parse_provider_query_param(self, request: Request) -> ProviderName | None:
        if (provider := request.get_str_input("provider")) is None or provider not in ProviderName:
            return None
        return ProviderName(provider)

    def _parse_sort_query_param(self, request: Request) -> SortType | None:
        if (sort_type := request.get_str_input("sort")) is None or sort_type not in SortType:
            return None
        return SortType(sort_type)

    def _parse_disabled_collapser(self, request: Request) -> bool:
        return request.get_str_input("collapse") is None

    def _collect_api_response_messages(
        self,
        result_counts: UnifiedSearchResultCounts,
    ) -> Sequence[UnifiedSearchApiResponseMessage]:
        messages = []
        if result_counts.monitoring == _LIVESTATUS_ENGINE_ROW_LIMIT:
            messages.append(
                UnifiedSearchApiResponseMessage(
                    header=_(
                        "Display limit of %(_LIVESTATUS_ENGINE_ROW_LIMIT)d monitoring results reached."
                    )
                    % {"_LIVESTATUS_ENGINE_ROW_LIMIT": _LIVESTATUS_ENGINE_ROW_LIMIT},
                    detail=_("Refine your search or press Enter for host/service search."),
                    message_variant=MessageVariant.info,
                )
            )
        return messages
