#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from fakeredis import FakeRedis

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.bi.aggregation_functions import BIAggregationFunctionWorst
from cmk.bi.filesystem import BIFileSystem
from cmk.bi.lib import BIAggregationComputationOptions, BIAggregationGroups
from cmk.bi.rule_interface import BIRuleProperties
from cmk.bi.storage import (
    AggregationNotFound,
    AggregationStore,
    FrozenAggregationStore,
    generate_identifier,
    LookupStore,
    MetadataStore,
)
from cmk.bi.trees import BICompiledAggregation, BICompiledLeaf, BICompiledRule
from cmk.bi.type_defs import ComputationConfigDict


class TestAggregationStore:
    @pytest.fixture
    def aggregation_store(self, fs: BIFileSystem) -> AggregationStore:
        return AggregationStore(fs.cache)

    def test_save_and_get(self, aggregation_store: AggregationStore) -> None:
        aggregation = _build_aggregation("myaggregation")
        aggregation_store.save(aggregation)

        assert aggregation_store.get("myaggregation").id == "myaggregation"

    def test_missing_aggregation(self, aggregation_store: AggregationStore) -> None:
        with pytest.raises(AggregationNotFound):
            aggregation_store.get_by_identifier(generate_identifier("does-not-exist-in-store"))

    def test_yield_stored_identifiers(self, aggregation_store: AggregationStore) -> None:
        aggregation_store.save(heute_aggregation := _build_aggregation("heute"))
        aggregation_store.save(gestern_aggregation := _build_aggregation("gestern"))

        value = set(aggregation_store.yield_stored_identifiers())
        expected = {
            generate_identifier(heute_aggregation.id),
            generate_identifier(gestern_aggregation.id),
        }

        assert value == expected

    def test_no_stored_identifiers(self, aggregation_store: AggregationStore) -> None:
        assert not any(aggregation_store.yield_stored_identifiers())

    def test_idempotentency(self, aggregation_store: AggregationStore) -> None:
        aggregation = _build_aggregation("heute")
        aggregation_identifier = generate_identifier(aggregation.id)

        aggregation_store.save(aggregation)
        aggregation_store.save(aggregation)
        assert len(list(aggregation_store.yield_stored_identifiers())) == 1

        aggregation_store.delete_by_identifier(aggregation_identifier)
        aggregation_store.delete_by_identifier(aggregation_identifier)
        assert len(list(aggregation_store.yield_stored_identifiers())) == 0

    def test_multiple_aggregations_workflow(self, aggregation_store: AggregationStore) -> None:
        aggregation_store.save(_build_aggregation("heute"))
        aggregation_store.save(_build_aggregation("gestern"))

        assert len(stored_identifiers := list(aggregation_store.yield_stored_identifiers())) == 2

        for identifier in stored_identifiers:
            aggregation_store.delete_by_identifier(identifier)

        assert len(list(aggregation_store.yield_stored_identifiers())) == 0


class TestFrozenAggregationStore:
    @pytest.fixture
    def frozen_store(self, fs: BIFileSystem) -> FrozenAggregationStore:
        return FrozenAggregationStore(fs.var)

    def test_save_and_get(self, frozen_store: FrozenAggregationStore) -> None:
        branch = _build_branch("My Branch")
        aggregation = _build_aggregation("myaggregation", branches=[branch])
        aggregation.id = "frozen_myaggregation_My Branch"
        frozen_store.save(aggregation, "myaggregation", "My Branch")

        assert (frozen_agg := frozen_store.get("myaggregation", "My Branch"))
        assert frozen_agg.id == "frozen_myaggregation_My Branch"
        assert frozen_store.exists("myaggregation", "My Branch")

    def test_missing_aggregation(self, frozen_store: FrozenAggregationStore) -> None:
        assert frozen_store.get("myaggregation", "Foo Branch") is None
        assert frozen_store.exists("myaggregation", "Foo Branch") is False

    def test_delete_is_idempotent(self, frozen_store: FrozenAggregationStore) -> None:
        frozen_store.delete("heute")
        frozen_store.delete("heute")  # shouldn't raise


class TestMetadataStore:
    @pytest.fixture
    def metadata_store(self, fs: BIFileSystem) -> MetadataStore:
        return MetadataStore(fs)

    def test_update_last_compilation(self, metadata_store: MetadataStore) -> None:
        assert metadata_store.get_last_compilation() == 0.0
        timestamp = 123456789.0
        metadata_store.update_last_compilation(timestamp)
        assert metadata_store.get_last_compilation() == timestamp

    def test_last_configuration_change_default(self, metadata_store: MetadataStore) -> None:
        assert metadata_store.get_last_config_change() == 0.0

    def test_last_config_change_bi_config(self, metadata_store: MetadataStore) -> None:
        metadata_store.fs.etc.config.touch()
        assert metadata_store.get_last_config_change() > 0.0

    def test_last_config_change_general_config(self, metadata_store: MetadataStore) -> None:
        (metadata_store.fs.etc.multisite / "general.mk").touch()
        assert metadata_store.get_last_config_change() > 0.0


class TestLookupStore:
    @pytest.fixture
    def lookup_store(self) -> LookupStore:
        return LookupStore(FakeRedis())

    def get_compiled_aggregrations(self) -> dict[str, BICompiledAggregation]:
        return {"heute": _build_aggregation("heute", branches=[_build_branch("Host heute")])}

    def test_base_lookup_key_does_not_exists(self, lookup_store: LookupStore) -> None:
        assert not lookup_store.base_lookup_key_exists()

    def test_base_lookup_key_exists(self, lookup_store: LookupStore) -> None:
        lookup_store.generate_aggregation_lookups({})
        assert lookup_store.base_lookup_key_exists()

    def test_lookup_aggregation_does_not_exists(self, lookup_store: LookupStore) -> None:
        assert not lookup_store.aggregation_lookup_exists("foo", "bar")

    def test_lookup_aggregation_exists(self, lookup_store: LookupStore) -> None:
        compiled_aggregations = self.get_compiled_aggregrations()
        lookup_store.generate_aggregation_lookups(compiled_aggregations)
        assert lookup_store.aggregation_lookup_exists("heute", None)

    def test_lookup_aggregation_exists_with_lock(self, lookup_store: LookupStore) -> None:
        with lookup_store.get_aggregation_lookup_lock():
            compiled_aggregations = self.get_compiled_aggregrations()
            lookup_store.generate_aggregation_lookups(compiled_aggregations)

        assert lookup_store.aggregation_lookup_exists("heute", None)


def test_identifier_handles_long_aggregation_ids() -> None:
    aggregation_id = """rsentoanfukkexikcuduwfywktekresvkfu_seriieorf;rnetinrsdknerfuornserf?fentn\
irnsteirnsetrsdkuftzfvnrskvrsufwyywfv/rsetnriesntfutkresoinaervkufvoywuveongarsevrsvkrsngmwfuyerre\
irnsteirnsetrsdkuftzfvnrskvrsufwyywfv/rsetnriesntfutkresoinaervkufvoywuveongarsevrsvkrsngmwfuyer"""
    assert len(generate_identifier(aggregation_id)) < 255


def test_identifier_creates_consistent_ids_based_on_input() -> None:
    assert generate_identifier("heute") == generate_identifier("heute")


def _build_branch(title: str) -> BICompiledRule:
    return BICompiledRule(
        rule_id="hostcheck",
        pack_id="default",
        nodes=[BICompiledLeaf(host_name=HostName("heute"), site_id="heute")],
        required_hosts=[(SiteId("heute"), HostName("heute"))],
        properties=BIRuleProperties(
            {"title": title, "comment": "", "docu_url": "", "icon": "", "state_messages": {}}
        ),
        aggregation_function=BIAggregationFunctionWorst(
            {"type": "worst", "count": 1, "restrict_state": 2}
        ),
        node_visualization={"style_config": {}, "type": "none"},
    )


def _build_aggregation(
    aggregation_id: str, *, branches: list[BICompiledRule] | None = None
) -> BICompiledAggregation:
    return BICompiledAggregation(
        aggregation_id=aggregation_id,
        branches=branches or [],
        computation_options=BIAggregationComputationOptions(
            ComputationConfigDict(
                disabled=False, use_hard_states=False, escalate_downtimes_as_warn=False
            )
        ),
        aggregation_visualization={},
        groups=BIAggregationGroups(
            {
                "names": ["groupA", "groupB"],
                "paths": [["path", "group", "a"], ["path", "group", "b"]],
            }
        ),
    )
