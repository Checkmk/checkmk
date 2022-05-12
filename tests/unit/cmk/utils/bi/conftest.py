#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Optional

import pytest

from livestatus import LivestatusOutputFormat, LivestatusResponse

from cmk.utils.bi.bi_data_fetcher import BIStatusFetcher, BIStructureFetcher
from cmk.utils.bi.bi_lib import SitesCallback
from cmk.utils.bi.bi_node_generator import BINodeGenerator
from cmk.utils.bi.bi_packs import BIAggregationPacks
from cmk.utils.bi.bi_rule import BIRule
from cmk.utils.bi.bi_rule_interface import bi_rule_id_registry
from cmk.utils.bi.bi_searcher import BISearcher

from .bi_test_data import sample_config


class MockBIAggregationPack(BIAggregationPacks):
    def __init__(self, config: Dict[Any, Any]):
        super().__init__("")
        self._load_config(config)

    def load_config(self) -> None:
        pass

    def save_config(self) -> None:
        pass


def mock_query_callback(
    query: str,
    only_sites: Optional[List[str]] = None,
    output_format: LivestatusOutputFormat = LivestatusOutputFormat.PYTHON,
) -> LivestatusResponse:
    return LivestatusResponse([])


@pytest.fixture(scope="function", name="bi_searcher")
def _bi_searcher():
    yield BISearcher()


@pytest.fixture(scope="function")
def bi_searcher_with_sample_config(bi_searcher):
    structure_fetcher = BIStructureFetcher(SitesCallback(lambda: None, mock_query_callback))
    structure_fetcher.add_site_data("heute", sample_config.bi_structure_states)
    bi_searcher.set_hosts(structure_fetcher.hosts)
    yield bi_searcher


@pytest.fixture(scope="function")
def bi_status_fetcher():
    status_fetcher = BIStatusFetcher(SitesCallback(lambda: None, mock_query_callback))
    yield status_fetcher


@pytest.fixture(scope="function")
def bi_structure_fetcher():
    structure_fetcher = BIStructureFetcher(SitesCallback(lambda: None, mock_query_callback))
    yield structure_fetcher


@pytest.fixture(scope="function")
def dummy_bi_rule():
    rule_id = "dummy_rule"
    try:
        node_schema = BINodeGenerator.schema()().dump({})
        node_schema["action"]["host_regex"] = "heute_clone"
        schema_config = BIRule.schema()().dump({"id": rule_id})
        schema_config["nodes"].append(node_schema)
        yield BIRule(schema_config)
    finally:
        bi_rule_id_registry.unregister(rule_id)


@pytest.fixture(scope="function")
def bi_packs_sample_config():
    yield MockBIAggregationPack(sample_config.bi_packs_config)
