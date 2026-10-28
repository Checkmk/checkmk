#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.http import Request
from cmk.gui.monitor.hosts.page_url import all_hosts_url
from cmk.gui.monitor.hosts.search_filters import host_search_filter, UnsupportedSearchError
from cmk.gui.pages import Page, PageContext
from cmk.gui.search.spec import parse, SearchParseError, UnprefixedSearch
from cmk.ruleset_matcher.tags import TagConfig

_QUERY_VAR = "q"


class MonitorRouterPage(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        query = ctx.request.get_str_input_mandatory(_QUERY_VAR, "")
        raise HTTPRedirect(route(ctx.request, query, ctx.config.tags))


def route(request: Request, query: str, tags: TagConfig) -> str:
    """Builds a monitoring URL based on the result of the query.

    Raises:
        MKUserError: if the query is invalid or no page can filter on it yet.
    """
    try:
        spec = parse(query)
        if isinstance(spec, UnprefixedSearch):
            # As typed, with control characters as spaces: the page turns "*" into ".*" itself,
            # but drops control characters, which would join the words.
            return all_hosts_url(request, search=spec.text)
        return all_hosts_url(request, filter_node=host_search_filter(spec, tags))
    except (SearchParseError, UnsupportedSearchError) as e:
        raise MKUserError(_QUERY_VAR, str(e)) from e
