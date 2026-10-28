#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import override

from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import Request
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.monitor.hosts.page_url import all_hosts_url
from cmk.gui.monitor.hosts.search_filters import host_search_filter
from cmk.gui.monitor.hosts.table import FilterNode, HostTable, MonitorFolders
from cmk.gui.monitor.services.page_url import all_services_url, host_services_url
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


@dataclass(frozen=True)
class FoundHost:
    name: str
    site_id: str


type OnlyHost = Callable[[FilterNode | None, str], FoundHost | None]
"""The host All hosts would list alone for a filter and a search box text, else None."""

type OnlyHostSource = Callable[[PageContext], OnlyHost]


def livestatus_only_host(setup_folders: SetupFolderSource) -> OnlyHostSource:
    """Asks the hosts table, which All hosts lists from, for the host a search finds alone."""

    def source(ctx: PageContext) -> OnlyHost:
        def only_host(filter_node: FilterNode | None, search: str) -> FoundHost | None:
            table = HostTable(ctx.config.sites, MonitorFolders(setup_folders(ctx.config, user)))
            host = table.only_host(query=search, filter_node=filter_node)
            return None if host is None else FoundHost(name=host.name, site_id=host.site_id)

        return only_host

    return source


class MonitorRouterPage(Page):
    def __init__(self, setup_folders: SetupFolderSource, only_host: OnlyHostSource) -> None:
        self._setup_folders = setup_folders
        self._only_host = only_host

    @override
    def page(self, ctx: PageContext) -> None:
        query = ctx.request.get_str_input_mandatory(_QUERY_VAR, "")
        raise HTTPRedirect(
            route(
                ctx.request,
                query,
                ctx.config.tags,
                lambda: self._setup_folders(ctx.config, user).all_titles(),
                self._only_host(ctx),
            )
        )


def route(
    request: Request,
    query: str,
    tags: TagConfig,
    folders: Callable[[], Mapping[str, str]],
    only_host: OnlyHost,
) -> str:
    """Builds a monitoring URL based on the result of the query.

    ``folders`` are Setup's folder titles by path, only asked for when the query names a folder.

    A host search that finds a single host opens Services of that host with its host panel rather
    than All hosts with one row, as ``only_host`` tells.

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
        return _hosts_url(request, only_host, None, spec.text)
    try:
        if _searches_services(spec):
            return all_services_url(request, filter_node=service_search_filter(spec))
        return _hosts_url(request, only_host, host_search_filter(spec, tags, folders), "")
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


def _hosts_url(
    request: Request, only_host: OnlyHost, filter_node: FilterNode | None, search: str
) -> str:
    url = all_hosts_url(request, filter_node=filter_node, search=search)
    if (host := only_host(filter_node, search)) is None:
        return url
    return host_services_url(
        request, host_name=host.name, site_id=host.site_id, open_host_panel=True
    )


def _searches_services(spec: PrefixedSearch) -> bool:
    return any(
        isinstance(term, ServiceName | ServiceGroup | ServiceState | ServiceLabel | ServiceFolder)
        for clause in spec.clauses
        for term in clause
    )
