#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Iterator
from typing import NamedTuple

from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry

from cmk.utils.servicename import ServiceName

from cmk.bi.data_fetcher import BIStatusFetcher
from cmk.bi.lib import NodeResultBundle, RequiredBIElement
from cmk.bi.trees import BICompiledAggregation, BICompiledRule


class BIAggregationFilter(NamedTuple):
    hosts: list[HostName]
    services: list[tuple[HostName, ServiceName]]
    aggr_ids: list[str]
    aggr_titles: list[str]
    group_names: list[str]
    group_path_prefix: list[str]


class ABCPostprocessComputeResult:
    def postprocess(
        self, bi_aggregation: BICompiledAggregation, node_result_bundle: NodeResultBundle
    ) -> NodeResultBundle:
        raise NotImplementedError()


class BIComputerPostprocessingRegistry(Registry[ABCPostprocessComputeResult]):
    def plugin_name(self, instance: ABCPostprocessComputeResult) -> str:
        return instance.__class__.__name__

    def postprocess(
        self,
        compiled_aggregation: BICompiledAggregation,
        node_result_bundles: list[NodeResultBundle],
    ) -> Iterator[NodeResultBundle]:
        for node_result_bundle in node_result_bundles:
            postprocessed_bundle = node_result_bundle
            for postprocessor in self.values():
                postprocessed_bundle = postprocessor.postprocess(
                    compiled_aggregation, postprocessed_bundle
                )
            yield postprocessed_bundle


bi_computer_postprocessing_registry = BIComputerPostprocessingRegistry()


class BIComputer:
    def __init__(
        self,
        compiled_aggregations: dict[str, BICompiledAggregation],
        bi_status_fetcher: BIStatusFetcher,
    ) -> None:
        self._compiled_aggregations = compiled_aggregations
        self._bi_status_fetcher = bi_status_fetcher
        self._legacy_branch_cache: dict = {}

    def compute_aggregation_result(
        self,
        aggr_id: str,
        title: str,
    ) -> list[tuple[BICompiledAggregation, list[NodeResultBundle]]]:
        compiled_aggregation: BICompiledAggregation | None = self._compiled_aggregations.get(
            aggr_id
        )

        if not compiled_aggregation:
            return []

        for branch in compiled_aggregation.branches:
            if branch.properties.title == title:
                return self.compute_results([(compiled_aggregation, [branch])])
        return []

    def compute_result_for_filter(
        self, bi_aggregation_filter: BIAggregationFilter
    ) -> list[tuple[BICompiledAggregation, list[NodeResultBundle]]]:
        required_aggregations = self.get_required_aggregations(bi_aggregation_filter)
        required_elements = self.get_required_elements(required_aggregations)
        self._bi_status_fetcher.update_states(required_elements)
        return self.compute_results(required_aggregations)

    def get_required_aggregations(
        self, bi_aggregation_filter: BIAggregationFilter
    ) -> list[tuple[BICompiledAggregation, list[BICompiledRule]]]:
        return [
            (
                compiled_aggregation,
                self.get_filtered_aggregation_branches(compiled_aggregation, bi_aggregation_filter),
            )
            for compiled_aggregation in self._compiled_aggregations.values()
        ]

    def get_required_elements(
        self, required_aggregations: list[tuple[BICompiledAggregation, list[BICompiledRule]]]
    ) -> set[RequiredBIElement]:
        required_elements = set()
        for _compiled_aggregation, branches in required_aggregations:
            for branch in branches:
                required_elements.update(branch.required_elements())
        return required_elements

    def compute_results(
        self, required_aggregations: list[tuple[BICompiledAggregation, list[BICompiledRule]]]
    ) -> list[tuple[BICompiledAggregation, list[NodeResultBundle]]]:
        results = []
        for compiled_aggregation, branches in required_aggregations:
            node_result_bundles = compiled_aggregation.compute_branches(
                branches,
                self._bi_status_fetcher,
            )

            # Postprocess results. Custom user plugins may add additional information for each node
            node_result_bundles = list(
                bi_computer_postprocessing_registry.postprocess(
                    compiled_aggregation,
                    node_result_bundles,
                )
            )

            results.append((compiled_aggregation, node_result_bundles))
        return results

    def get_filtered_aggregation_branches(
        self,
        compiled_aggregation: BICompiledAggregation,
        bi_aggregation_filter: BIAggregationFilter,
    ) -> list[BICompiledRule]:
        if not self._use_aggregation(compiled_aggregation, bi_aggregation_filter):
            return []

        return [
            compiled_branch
            for compiled_branch in compiled_aggregation.branches
            if self._use_aggregation_branch(compiled_branch, bi_aggregation_filter)
        ]

    def _use_aggregation(
        self,
        compiled_aggregation: BICompiledAggregation,
        bi_aggregation_filter: BIAggregationFilter,
    ) -> bool:
        # Filter aggregation ID
        if (
            bi_aggregation_filter.aggr_ids
            and compiled_aggregation.id not in bi_aggregation_filter.aggr_ids
        ):
            return False

        # Filter aggregation group names
        # Note: Paths are also available as names
        if bi_aggregation_filter.group_names and (
            len(
                compiled_aggregation.groups.combined_groups().intersection(
                    bi_aggregation_filter.group_names
                )
            )
            == 0
        ):
            return False

        # Filter aggregation group paths
        group_paths = compiled_aggregation.groups.paths
        return bool(
            not bi_aggregation_filter.group_path_prefix
            or self._matches_group_path(group_paths, bi_aggregation_filter.group_path_prefix)
        )

    def _use_aggregation_branch(
        self, compiled_branch: BICompiledRule, bi_aggregation_filter: BIAggregationFilter
    ) -> bool:
        branch_elements = compiled_branch.required_elements()
        branch_hosts = {x[1] for x in branch_elements}
        branch_services = {(x[1], x[2]) for x in branch_elements if x[2] is not None}
        if bi_aggregation_filter.hosts and not branch_hosts.intersection(
            bi_aggregation_filter.hosts
        ):
            return False

        if bi_aggregation_filter.services and not branch_services.intersection(
            bi_aggregation_filter.services
        ):
            return False

        return (
            not bi_aggregation_filter.aggr_titles
            or compiled_branch.properties.title in bi_aggregation_filter.aggr_titles
        )

    #   .--Legacy--------------------------------------------------------------.
    #   |                  _                                                   |
    #   |                 | |    ___  __ _  __ _  ___ _   _                    |
    #   |                 | |   / _ \/ _` |/ _` |/ __| | | |                   |
    #   |                 | |__|  __/ (_| | (_| | (__| |_| |                   |
    #   |                 |_____\___|\__, |\__,_|\___|\__, |                   |
    #   |                            |___/            |___/                    |
    #   +----------------------------------------------------------------------+

    def compute_legacy_result_for_filter(
        self, bi_aggregation_filter: BIAggregationFilter
    ) -> list[dict]:
        results = self.compute_result_for_filter(bi_aggregation_filter)
        return self.convert_to_legacy_results(results, bi_aggregation_filter)

    def convert_to_legacy_results(
        self,
        results: list[tuple[BICompiledAggregation, list[NodeResultBundle]]],
        bi_aggregation_filter: BIAggregationFilter,
    ) -> list[dict]:
        try:
            return self._legacy_postprocessing(results, bi_aggregation_filter)
        finally:
            self._legacy_branch_cache = {}

    def _legacy_postprocessing(
        self,
        results: list[tuple[BICompiledAggregation, list[NodeResultBundle]]],
        bi_aggregation_filter: BIAggregationFilter,
    ) -> list[dict]:
        legacy_results = []
        # Create one result for each bi group name/path
        for compiled_aggregation, branches in results:
            matched_aggr_groups = self._get_matched_aggr_groups(
                bi_aggregation_filter,
                compiled_aggregation,
            )

            for aggr_group in matched_aggr_groups:
                for branch in branches:
                    legacy_results.append(
                        self._get_legacy_branch(compiled_aggregation, branch, aggr_group)
                    )

        return legacy_results

    def _get_matched_aggr_groups(
        self,
        bi_aggregation_filter: BIAggregationFilter,
        compiled_aggregation: BICompiledAggregation,
    ) -> set[str]:
        filter_names = bi_aggregation_filter.group_names
        filter_paths = bi_aggregation_filter.group_path_prefix

        compiled_aggr_group_names = set(
            compiled_aggregation.groups.names
            + ["/".join(x) for x in compiled_aggregation.groups.paths]
        )
        if not filter_names and not filter_paths:
            return compiled_aggr_group_names

        matched_aggr_groups = set()
        for group_name in compiled_aggr_group_names:
            for filter_name in filter_names:
                if group_name.startswith(filter_name):
                    matched_aggr_groups.add(group_name)
                    break

        for group_path in compiled_aggregation.groups.paths:
            if self._matches_group_path([group_path], filter_paths):
                matched_aggr_groups.add("/".join(group_path))

        return matched_aggr_groups

    def _matches_group_path(self, group_paths: list[list[str]], filter_paths: list[str]) -> bool:
        for filter_path in filter_paths:
            for group_path in group_paths:
                if "/".join(group_path).startswith(filter_path):
                    return True
        return False

    def _get_legacy_branch(
        self,
        compiled_aggregation: BICompiledAggregation,
        node_result_bundle: NodeResultBundle,
        aggr_group: str,
    ) -> dict:
        title = node_result_bundle.instance.properties.title
        if title not in self._legacy_branch_cache:
            legacy_branch = compiled_aggregation.convert_result_to_legacy_format(node_result_bundle)
            self._legacy_branch_cache[title] = legacy_branch
        else:
            legacy_branch = copy.deepcopy(self._legacy_branch_cache[title])
        legacy_branch["aggr_group"] = aggr_group
        return legacy_branch
