#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from cmk.bi.compiler import BICompiler
from cmk.bi.computer import BIComputer
from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.filesystem import get_default_site_filesystem
from cmk.bi.storage import AggregationNotFound, AggregationStore
from cmk.bi.trees import (
    BICompiledAggregation,
    BICompiledRule,
    get_compiled_aggregation_and_branch_by_name,
)
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.hooks import request_memoize

from ._filesystem import get_bi_config_path
from ._sites_callback import create_default_sites_callback


class BIManager:
    def __init__(self) -> None:
        sites_callback = create_default_sites_callback()
        self.compiler = BICompiler(get_bi_config_path(), sites_callback)
        self.compiler.load_compiled_aggregations()
        self.status_fetcher = BIStatusFetcher(sites_callback)
        self.computer = BIComputer(self.compiler.compiled_aggregations, self.status_fetcher)

    def get_aggregation_by_name(self, name: str) -> tuple[BICompiledAggregation, BICompiledRule]:
        return get_compiled_aggregation_and_branch_by_name(
            compiled_aggregations=self.compiler.compiled_aggregations,
            aggr_name=name,
        )


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
