#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import NamedTuple, List, Tuple, Set, Dict, Optional
from contextlib import contextmanager

from cmk.utils.type_defs import ServiceName
from cmk.utils.bi.bi_lib import RequiredBIElement
from cmk.utils.bi.bi_data_fetcher import BIHostSpec, bi_status_fetcher
from cmk.utils.bi.bi_compiler import bi_compiler, bi_compiler_auto_cleanup
from cmk.utils.bi.bi_trees import BICompiledRule, BICompiledAggregation, NodeResultBundle

BIAggregationFilter = NamedTuple("BIAggregationFilter", [
    ("hosts", List[BIHostSpec]),
    ("services", List[Tuple[BIHostSpec, ServiceName]]),
    ("aggr_ids", List[str]),
    ("aggr_titles", List[str]),
    ("group_names", List[str]),
    ("group_path_prefix", List[str]),
])


class BIComputer:
    def __init__(self):
        self._legacy_branch_cache = {}

    def compute_aggregation_result(
        self,
        aggr_id: str,
        title: str,
    ) -> List[Tuple[BICompiledAggregation, List[NodeResultBundle]]]:
        compiled_aggregation: Optional[
            BICompiledAggregation] = bi_compiler.compiled_aggregations.get(aggr_id)

        if not compiled_aggregation:
            return []

        for branch in compiled_aggregation.branches:
            if branch.properties.title == title:
                return self.compute_results([(compiled_aggregation, [branch])])
        return []

    def compute_result_for_filter(
        self, bi_aggregation_filter: BIAggregationFilter
    ) -> List[Tuple[BICompiledAggregation, List[NodeResultBundle]]]:
        required_aggregations = self.get_required_aggregations(bi_aggregation_filter)
        required_elements = self.get_required_elements(required_aggregations)
        bi_status_fetcher.update_states(required_elements)
        return self.compute_results(required_aggregations)

    def get_required_aggregations(
        self, bi_aggregation_filter: BIAggregationFilter
    ) -> List[Tuple[BICompiledAggregation, List[BICompiledRule]]]:
        return [(compiled_aggregation,
                 self.get_filtered_aggregation_branches(compiled_aggregation,
                                                        bi_aggregation_filter))
                for compiled_aggregation in bi_compiler.compiled_aggregations.values()]

    def get_required_elements(
        self, required_aggregations: List[Tuple[BICompiledAggregation, List[BICompiledRule]]]
    ) -> Set[RequiredBIElement]:
        required_elements = set()
        for _compiled_aggregation, branches in required_aggregations:
            for branch in branches:
                required_elements.update(branch.required_elements())
        return required_elements

    def compute_results(
        self, required_aggregations: List[Tuple[BICompiledAggregation, List[BICompiledRule]]]
    ) -> List[Tuple[BICompiledAggregation, List[NodeResultBundle]]]:
        results = []
        for compiled_aggregation, branches in required_aggregations:
            results.append((compiled_aggregation, compiled_aggregation.compute_branches(branches)))
        return results

    def get_filtered_aggregation_branches(
            self, compiled_aggregation: BICompiledAggregation,
            bi_aggregation_filter: BIAggregationFilter) -> List[BICompiledRule]:
        if not self._use_aggregation(compiled_aggregation, bi_aggregation_filter):
            return []

        used_branches = []
        for compiled_branch in compiled_aggregation.branches:
            if not self._use_aggregation_branch(compiled_branch, bi_aggregation_filter):
                continue
            used_branches.append(compiled_branch)
        return used_branches

    def _use_aggregation(self, compiled_aggregation: BICompiledAggregation,
                         bi_aggregation_filter: BIAggregationFilter) -> bool:
        # Filter aggregation ID
        if bi_aggregation_filter.aggr_ids and compiled_aggregation.id not in bi_aggregation_filter.aggr_ids:
            return False

        # Filter aggregation group names
        # Note: Paths are also available as names
        group_names = set(compiled_aggregation.groups.names +
                          ["/".join(x) for x in compiled_aggregation.groups.paths])
        if bi_aggregation_filter.group_names and len(
                group_names.intersection(bi_aggregation_filter.group_names)) == 0:
            return False

        # Filter aggregation group paths
        group_paths = compiled_aggregation.groups.paths
        if bi_aggregation_filter.group_path_prefix and not self._matches_group_path(
                group_paths, bi_aggregation_filter.group_path_prefix):
            return False

        return True

    def _use_aggregation_branch(self, compiled_branch: BICompiledRule,
                                bi_aggregation_filter: BIAggregationFilter) -> bool:
        required_elements = compiled_branch.required_elements()
        required_hosts = {x[1] for x in required_elements}
        required_services = {x[2] for x in required_elements if x[2] is not None}
        if bi_aggregation_filter.hosts and len(
                required_hosts.intersection(bi_aggregation_filter.hosts)) == 0:
            return False

        if bi_aggregation_filter.services and len(
                required_services.intersection(bi_aggregation_filter.services)) == 0:
            return False

        if bi_aggregation_filter.aggr_titles and compiled_branch.properties.title not in bi_aggregation_filter.aggr_titles:
            return False

        return True

    #   .--Legacy--------------------------------------------------------------.
    #   |                  _                                                   |
    #   |                 | |    ___  __ _  __ _  ___ _   _                    |
    #   |                 | |   / _ \/ _` |/ _` |/ __| | | |                   |
    #   |                 | |__|  __/ (_| | (_| | (__| |_| |                   |
    #   |                 |_____\___|\__, |\__,_|\___|\__, |                   |
    #   |                            |___/            |___/                    |
    #   +----------------------------------------------------------------------+

    def compute_legacy_result_for_filter(self,
                                         bi_aggregation_filter: BIAggregationFilter) -> List[Dict]:
        results = self.compute_result_for_filter(bi_aggregation_filter)
        legacy_results = bi_computer.convert_to_legacy_results(results, bi_aggregation_filter)
        return legacy_results

    def convert_to_legacy_results(self, results: List[Tuple[BICompiledAggregation,
                                                            List[NodeResultBundle]]],
                                  bi_aggregation_filter: BIAggregationFilter) -> List[Dict]:
        try:
            return self._legacy_postprocessing(results, bi_aggregation_filter)
        finally:
            self._legacy_branch_cache = {}

    def _legacy_postprocessing(self, results: List[Tuple[BICompiledAggregation,
                                                         List[NodeResultBundle]]],
                               bi_aggregation_filter: BIAggregationFilter) -> List[Dict]:
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
                        self._get_legacy_branch(compiled_aggregation, branch, aggr_group))

        return legacy_results

    def _get_matched_aggr_groups(self, bi_aggregation_filter: BIAggregationFilter,
                                 compiled_aggregation: BICompiledAggregation):
        filter_names = bi_aggregation_filter.group_names
        filter_paths = bi_aggregation_filter.group_path_prefix

        compiled_aggr_group_names = set(compiled_aggregation.groups.names +
                                        ["/".join(x) for x in compiled_aggregation.groups.paths])
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

    def _matches_group_path(self, group_paths: List[List[str]], filter_paths: List[str]) -> bool:
        for filter_path in filter_paths:
            for group_path in group_paths:
                if "/".join(group_path).startswith(filter_path):
                    return True
        return False

    def _get_legacy_branch(self, compiled_aggregation: BICompiledAggregation,
                           node_result_bundle: NodeResultBundle, aggr_group: str) -> Dict:
        title = node_result_bundle.instance.properties.title
        if title not in self._legacy_branch_cache:
            legacy_branch = compiled_aggregation.convert_result_to_legacy_format(node_result_bundle)
            self._legacy_branch_cache[title] = legacy_branch
        else:
            legacy_branch = copy.deepcopy(self._legacy_branch_cache[title])
        legacy_branch["aggr_group"] = aggr_group
        return legacy_branch


bi_computer = BIComputer()


@contextmanager
def bi_computer_auto_cleanup():
    try:
        with bi_compiler_auto_cleanup():
            yield bi_computer
    finally:
        # Free memory
        bi_status_fetcher.cleanup()
