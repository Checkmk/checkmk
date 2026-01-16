#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import override

from cmk.gui.http import Request
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.unified_search import ProviderName, SortType, UnifiedSearchApiResponse

from .collapsing import get_collapser
from .engines.customize import CustomizeSearchEngine
from .engines.monitoring import MonitoringSearchEngine
from .engines.setup import SetupSearchEngine
from .unified import UnifiedSearch


class PageUnifiedSearch(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        query = ctx.request.get_str_input_mandatory("q")
        provider = self._parse_provider_query_param(ctx.request)
        sort_type = self._parse_sort_query_param(ctx.request)
        collapser_disabled = self._parse_disabled_collapser(ctx.request)

        unified_search_engine = UnifiedSearch(
            setup_engine=SetupSearchEngine(ctx.config),
            monitoring_engine=MonitoringSearchEngine(
                UserPermissions.from_config(ctx.config, permission_registry)
            ),
            customize_engine=CustomizeSearchEngine(),
        )

        result = unified_search_engine.search(
            query,
            provider=provider,
            sort_type=sort_type,
        )

        collapse = get_collapser(provider=provider, disabled=collapser_disabled)
        search_results, search_count = collapse(result.results, result.counts)

        return asdict(
            UnifiedSearchApiResponse(
                url=ctx.request.url,
                query=query,
                counts=search_count,
                results=search_results,
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
