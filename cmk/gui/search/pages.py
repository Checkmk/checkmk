#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, get_args, override

from cmk.gui.http import request
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions

from .engines.customize import CustomizeSearchEngine
from .engines.monitoring import MonitoringSearchEngine
from .engines.setup import SetupSearchEngine
from .type_defs import Provider, SortType
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

        response = unified_search_engine.search(
            query,
            provider=provider,
            sort_type=sort_type,
        )

        return {
            "url": request.url,
            "query": query,
            "counts": response.counts.serialize(),
            "results": [result.serialize() for result in response.results],
        }

    def _parse_provider_query_param(self) -> Provider | None:
        if (provider := request.get_str_input("provider")) is None:
            return None

        return cast(Provider, provider) if provider in get_args(Provider) else None

    def _parse_sort_query_param(self) -> SortType | None:
        if (sort_type := request.get_str_input("sort")) is None:
            return None

        return cast(SortType, sort_type) if sort_type in get_args(SortType) else None
