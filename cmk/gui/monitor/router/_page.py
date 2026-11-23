#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import override

from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import Request
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.monitor.hosts.page_url import all_hosts_url
from cmk.gui.monitor.hosts.search_filters import host_search_filter, text_search_filters
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


type FirstHosts = Callable[[FilterNode], Sequence[FoundHost]]
"""Up to two of the hosts All hosts lists for a filter, see ``HostTable.first_hosts``."""

type FirstHostsSource = Callable[[PageContext], FirstHosts]


def livestatus_first_hosts(setup_folders: SetupFolderSource) -> FirstHostsSource:
    """Asks the hosts table, which All hosts lists from, for the first hosts a search finds."""

    def source(ctx: PageContext) -> FirstHosts:
        # Built on the first lookup, as a service query makes none, and shared by the next ones.
        @functools.cache
        def table() -> HostTable:
            return HostTable(ctx.config.sites, MonitorFolders(setup_folders(ctx.config, user)))

        def first_hosts(filter_node: FilterNode) -> Sequence[FoundHost]:
            return [
                FoundHost(name=host.name, site_id=host.site_id)
                for host in table().first_hosts(filter_node)
            ]

        return first_hosts

    return source


class MonitorRouterPage(Page):
    def __init__(self, setup_folders: SetupFolderSource, first_hosts: FirstHostsSource) -> None:
        self._setup_folders = setup_folders
        self._first_hosts = first_hosts

    @override
    def page(self, ctx: PageContext) -> None:
        query = ctx.request.get_str_input_mandatory(_QUERY_VAR, "")
        raise HTTPRedirect(
            route(
                ctx.request,
                query,
                ctx.config.tags,
                lambda: self._setup_folders(ctx.config, user).all_titles(),
                self._first_hosts(ctx),
            )
        )


def route(
    request: Request,
    query: str,
    tags: TagConfig,
    folders: Callable[[], Mapping[str, str]],
    first_hosts: FirstHosts,
) -> str:
    """Builds a monitoring URL based on the result of the query.

    ``folders`` are Setup's folder titles by path, only asked for when the query names a folder.

    A query without prefix opens the first of ``text_search_filters`` that finds hosts, else the
    search box of All hosts, as typed with control characters as spaces.

    A host search that finds a single host opens Services of that host with its host panel rather
    than All hosts with one row, as ``first_hosts`` tells.

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
        return _text_url(request, first_hosts, spec)
    try:
        if _searches_services(spec):
            return all_services_url(request, filter_node=service_search_filter(spec))
        filter_node = host_search_filter(spec, tags, folders)
        return _hosts_url(request, first_hosts(filter_node), filter_node)
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


def _text_url(request: Request, first_hosts: FirstHosts, spec: UnprefixedSearch) -> str:
    for filter_node in text_search_filters(spec):
        if found := first_hosts(filter_node):
            return _hosts_url(request, found, filter_node)
    return all_hosts_url(request, search=spec.text)


def _hosts_url(request: Request, found: Sequence[FoundHost], filter_node: FilterNode) -> str:
    match found:
        case [host]:
            return host_services_url(
                request, host_name=host.name, site_id=host.site_id, open_host_panel=True
            )
        case _:
            return all_hosts_url(request, filter_node=filter_node)


def _searches_services(spec: PrefixedSearch) -> bool:
    return any(
        isinstance(term, ServiceName | ServiceGroup | ServiceState | ServiceLabel | ServiceFolder)
        for clause in spec.clauses
        for term in clause
    )
