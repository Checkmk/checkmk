#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from pathlib import Path

from livestatus import LivestatusResponse, Query

from cmk.bi.compiler import BICompiler
from cmk.bi.computer import BIComputer
from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.filesystem import get_default_site_filesystem
from cmk.bi.lib import SitesCallback
from cmk.bi.storage import AggregationNotFound, AggregationStore
from cmk.bi.trees import BICompiledAggregation, BICompiledRule
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _


class BIManager:
    def __init__(self) -> None:
        sites_callback = SitesCallback(
            all_sites_with_id_and_online=all_sites_with_id_and_online,
            query=bi_livestatus_query,
            translate=_,
        )
        self.compiler = BICompiler(self.bi_configuration_file(), sites_callback)
        self.compiler.load_compiled_aggregations()
        self.status_fetcher = BIStatusFetcher(sites_callback)
        self.computer = BIComputer(self.compiler.compiled_aggregations, self.status_fetcher)

    @classmethod
    def bi_configuration_file(cls) -> Path:
        return get_default_site_filesystem().etc.config


def all_sites_with_id_and_online() -> list[tuple[SiteId, bool]]:
    return [
        (site_id, site_status["state"] == "online")
        for site_id, site_status in sites.states().items()
    ]


def bi_livestatus_query(
    query: Query,
    only_sites: list[SiteId] | None = None,
    fetch_full_data: bool = False,
) -> LivestatusResponse:
    with sites.only_sites(only_sites), sites.prepend_site():
        try:
            auth_domain = "bi_fetch_full_data" if fetch_full_data else "bi"
            sites.live().set_auth_domain(auth_domain)
            return sites.live().query(query)
        finally:
            sites.live().set_auth_domain("read")


@request_memoize(maxsize=10000)
def load_compiled_branch(aggr_id: str, branch_title: str) -> BICompiledRule:
    if compiled_aggregation := _load_compiled_aggregation(aggr_id):
        for branch in compiled_aggregation.branches:
            if branch.properties.title == branch_title:
                return branch
    raise MKGeneralException(f"Branch {branch_title} not found in aggregation {aggr_id}")


@request_memoize(maxsize=10000)
def _load_compiled_aggregation(aggr_id: str) -> BICompiledAggregation | None:
    try:
        return AggregationStore(get_default_site_filesystem().cache).get(aggr_id)
    except AggregationNotFound:
        return None
