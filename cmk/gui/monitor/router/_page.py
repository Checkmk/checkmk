#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import override

from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import Request
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.monitor.hosts.page_url import all_hosts_url
from cmk.gui.monitor.hosts.search_filters import host_search_filter
from cmk.gui.monitor.services.page_url import all_services_url
from cmk.gui.monitor.services.search_filters import service_search_filter
from cmk.gui.monitor.setup_folders import SetupFolderSource
from cmk.gui.pages import Page, PageContext
from cmk.gui.search.spec import (
    parse,
    prefix_of,
    PrefixedSearch,
    SearchParseError,
    ServiceFolder,
    ServiceGroup,
    ServiceLabel,
    ServiceName,
    ServiceState,
    UnprefixedSearch,
    UnsupportedSearchError,
)
from cmk.ruleset_matcher.tags import TagConfig
from cmk.web.utils.urls import makeuri_contextless

_QUERY_VAR = "q"


class MonitorRouterPage(Page):
    def __init__(self, setup_folders: SetupFolderSource) -> None:
        self._setup_folders = setup_folders

    @override
    def page(self, ctx: PageContext) -> None:
        query = ctx.request.get_str_input_mandatory(_QUERY_VAR, "")
        raise HTTPRedirect(
            route(
                ctx.request,
                query,
                ctx.config.tags,
                lambda: self._setup_folders(ctx.config, user).all_titles(),
            )
        )


def route(
    request: Request, query: str, tags: TagConfig, folders: Callable[[], Mapping[str, str]]
) -> str:
    """Builds a monitoring URL based on the result of the query.

    ``folders`` are Setup's folder titles by path, only asked for when the query names a folder.

    An invalid query goes to the search box of All hosts as typed: the page is where the user sees
    the query and corrects it. A query no page can filter on yet goes to the legacy search
    ``search_open.py``, which still shows it as before, and is logged by its prefixes and the
    reason, not by its values.
    """
    try:
        spec = parse(query)
    except SearchParseError:
        return all_hosts_url(request, search=query.strip())
    if isinstance(spec, UnprefixedSearch):
        # As typed, with control characters as spaces: the page turns "*" into ".*" itself,
        # but drops control characters, which would join the words.
        return all_hosts_url(request, search=spec.text)
    try:
        if _searches_services(spec):
            return all_services_url(request, filter_node=service_search_filter(spec))
        return all_hosts_url(request, filter_node=host_search_filter(spec, tags, folders))
    except UnsupportedSearchError as e:
        logger.warning(
            "Global search: no monitoring page can show a query with the prefixes %(prefixes)s"
            " (%(reason)s)",
            {
                "prefixes": ", ".join(
                    dict.fromkeys(f"{prefix_of(clause[0])}:" for clause in spec.clauses)
                ),
                "reason": e.reason,
            },
        )
        return makeuri_contextless(
            request, [(_QUERY_VAR, query.strip())], filename="search_open.py"
        )


def _searches_services(spec: PrefixedSearch) -> bool:
    return any(
        isinstance(term, ServiceName | ServiceGroup | ServiceState | ServiceLabel | ServiceFolder)
        for clause in spec.clauses
        for term in clause
    )
