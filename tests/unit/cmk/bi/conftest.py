#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Any

import pytest

from livestatus import LivestatusOutputFormat, LivestatusResponse, SiteId

from cmk.bi.data_fetcher import BIStatusFetcher, BIStructureFetcher
from cmk.bi.lib import SitesCallback
from cmk.bi.node_generator import BINodeGenerator
from cmk.bi.packs import BIAggregationPacks
from cmk.bi.rule import BIRule
from cmk.bi.rule_interface import bi_rule_id_registry
from cmk.bi.searcher import BISearcher


class MockBIAggregationPack(BIAggregationPacks):
    def __init__(self, config: dict[Any, Any]) -> None:
        super().__init__("")
        self._load_config(config)

    def load_config(self) -> None:
        pass

    def save_config(self) -> None:
        pass


def mock_query_callback(
    query: str,
    only_sites: list[SiteId] | None = None,
    output_format: LivestatusOutputFormat = LivestatusOutputFormat.PYTHON,
    fetch_full_data: bool = False,
) -> LivestatusResponse:
    return LivestatusResponse([])


DUMMY_SITES_CALLBACK = SitesCallback(lambda: [], mock_query_callback, lambda s: s)


@pytest.fixture(scope="function", name="bi_searcher")
def _bi_searcher() -> Iterator[BISearcher]:
    yield BISearcher()


@pytest.fixture(scope="function")
def bi_searcher_with_sample_config(bi_searcher: BISearcher) -> Iterator[BISearcher]:
    from .bi_test_data import sample_config

    structure_fetcher = BIStructureFetcher(DUMMY_SITES_CALLBACK)
    structure_fetcher.add_site_data(SiteId("heute"), sample_config.bi_structure_states)
    bi_searcher.set_hosts(structure_fetcher.hosts)
    yield bi_searcher


@pytest.fixture(scope="function")
def bi_status_fetcher() -> Iterator[BIStatusFetcher]:
    status_fetcher = BIStatusFetcher(DUMMY_SITES_CALLBACK)
    yield status_fetcher


@pytest.fixture(scope="function")
def bi_structure_fetcher() -> Iterator[BIStructureFetcher]:
    structure_fetcher = BIStructureFetcher(DUMMY_SITES_CALLBACK)
    yield structure_fetcher


@pytest.fixture(scope="function")
def dummy_bi_rule() -> Iterator[BIRule]:
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
def bi_packs_sample_config() -> Iterator[BIAggregationPacks]:
    from .bi_test_data import sample_config

    yield MockBIAggregationPack(sample_config.bi_packs_config)
