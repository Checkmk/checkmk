#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import override

from cmk.gui.http import request
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.unified_search import ProviderName, SortType, UnifiedSearchApiResponse

from .engines.customize import CustomizeSearchEngine
from .engines.monitoring import MonitoringSearchEngine
from .engines.setup import SetupSearchEngine
from .unified import UnifiedSearch


class PageUnifiedSearch(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        query = request.get_str_input_mandatory("q")
        provider = self._parse_provider_query_param()
        sort_type = self._parse_sort_query_param()

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

        return asdict(
            UnifiedSearchApiResponse(
                url=request.url,
                query=query,
                counts=result.counts,
                results=result.results,
            )
        )

    def _parse_provider_query_param(self) -> ProviderName | None:
        if (provider := request.get_str_input("provider")) is None:
            return None
        try:
            return ProviderName(provider)
        except ValueError:
            return None

    def _parse_sort_query_param(self) -> SortType | None:
        if (sort_type := request.get_str_input("sort")) is None:
            return None
        try:
            return SortType(sort_type)
        except ValueError:
            return None
