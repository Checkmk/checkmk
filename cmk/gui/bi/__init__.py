#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Any

from cmk.utils.type_defs import HostName, ServiceName

import cmk.gui.pages
import cmk.gui.utils
import cmk.gui.view_utils
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.valuespec import DropdownChoiceEntries

from cmk.bi.compiler import BICompiler
from cmk.bi.computer import BIAggregationFilter
from cmk.bi.lib import BIStates, NodeResultBundle, SitesCallback
from cmk.bi.packs import BIAggregationPacks
from cmk.bi.trees import BICompiledRule

from .bi_manager import all_sites_with_id_and_online, bi_livestatus_query, BIManager
from .foldable_tree_renderer import (
    ABCFoldableTreeRenderer,
    FoldableTreeRendererBottomUp,
    FoldableTreeRendererBoxes,
    FoldableTreeRendererTopDown,
    FoldableTreeRendererTree,
)
from .helpers import get_state_assumption_key


# Move everything to .registration once extracted from __init__
def register() -> None:
    cmk.gui.pages.register("bi_set_assumption")(ajax_set_assumption)
    cmk.gui.pages.register("bi_save_treestate")(ajax_save_treestate)
    cmk.gui.pages.register("bi_render_tree")(ajax_render_tree)


def is_part_of_aggregation(host, service) -> bool:  # type:ignore[no-untyped-def]
    if BIAggregationPacks.get_num_enabled_aggregations() == 0:
        return False
    return _get_cached_bi_compiler().is_part_of_aggregation(host, service)


@request_memoize()
def _get_cached_bi_compiler() -> BICompiler:
    return BICompiler(
        BIManager.bi_configuration_file(),
        SitesCallback(all_sites_with_id_and_online, bi_livestatus_query, _),
    )


def get_aggregation_group_trees():
    # Here we have to deal with weird legacy
    # aggregation group definitions:
    # - "GROUP"
    # - ["GROUP_1", "GROUP2", ..]

    return get_cached_bi_packs().get_aggregation_group_trees()


def aggregation_group_choices() -> DropdownChoiceEntries:
    """Returns a sorted list of aggregation group names"""
    return get_cached_bi_packs().get_aggregation_group_choices()


def api_get_aggregation_state(  # type:ignore[no-untyped-def]
    filter_names: list[str] | None = None, filter_groups: list[str] | None = None
):
    bi_manager = BIManager()
    bi_aggregation_filter = BIAggregationFilter(
        [],
        [],
        [],
        filter_names or [],
        filter_groups or [],
        [],
    )

    def collect_infos(  # type:ignore[no-untyped-def]
        node_result_bundle: NodeResultBundle, is_single_host_aggregation: bool
    ):
        actual_result = node_result_bundle.actual_result

        own_infos = {}
        if actual_result.custom_infos:
            own_infos["custom"] = actual_result.custom_infos

        if actual_result.state not in [BIStates.OK, BIStates.PENDING]:
            node_instance = node_result_bundle.instance
            line_tokens = []
            if isinstance(node_instance, BICompiledRule):
                line_tokens.append(node_instance.properties.title)
            else:
                node_info = []
                if not is_single_host_aggregation:
                    node_info.append(node_instance.host_name)
                if node_instance.service_description:
                    node_info.append(node_instance.service_description)
                if node_info:
                    line_tokens.append("/".join(node_info))
            if actual_result.output:
                line_tokens.append(actual_result.output)
            own_infos["error"] = {"state": actual_result.state, "output": ", ".join(line_tokens)}

        nested_infos = [
            x
            for y in node_result_bundle.nested_results
            for x in [collect_infos(y, is_single_host_aggregation)]
            if x is not None
        ]

        if own_infos or nested_infos:
            return [own_infos, nested_infos]
        return None

    aggregations = {}
    results = bi_manager.computer.compute_result_for_filter(bi_aggregation_filter)
    for _compiled_aggregation, node_result_bundles in results:
        for node_result_bundle in node_result_bundles:
            aggr_title = node_result_bundle.instance.properties.title
            required_hosts = [x[1] for x in node_result_bundle.instance.get_required_hosts()]
            is_single_host_aggregation = len(required_hosts) == 1
            aggregations[aggr_title] = {
                "state": node_result_bundle.actual_result.state,
                "output": node_result_bundle.actual_result.output,
                "hosts": required_hosts,
                "acknowledged": node_result_bundle.actual_result.acknowledged,
                "in_downtime": node_result_bundle.actual_result.downtime_state != 0,
                "in_service_period": node_result_bundle.actual_result.in_service_period,
                "infos": collect_infos(node_result_bundle, is_single_host_aggregation),
            }

    have_sites = {x[0] for x in bi_manager.status_fetcher.states}
    missing_aggregations = []
    required_sites = set()
    required_aggregations = bi_manager.computer.get_required_aggregations(bi_aggregation_filter)
    for _bi_aggregation, branches in required_aggregations:
        for branch in branches:
            branch_sites = {x[0] for x in branch.required_elements()}
            required_sites.update(branch_sites)
            if branch.properties.title not in aggregations:
                missing_aggregations.append(branch.properties.title)

    response = {
        "aggregations": aggregations,
        "missing_sites": list(required_sites - have_sites),
        "missing_aggr": missing_aggregations,
    }
    return response


def ajax_set_assumption() -> None:
    site = request.get_str_input("site")
    host = request.get_str_input("host")
    service = request.get_str_input("service")
    state = request.var("state")
    if state == "none":
        del user.bi_assumptions[get_state_assumption_key(site, host, service)]
    elif state is not None:
        user.bi_assumptions[get_state_assumption_key(site, host, service)] = int(state)
    else:
        raise Exception("ajax_set_assumption: state is None")
    user.save_bi_assumptions()


def ajax_save_treestate():
    path_id = request.get_str_input_mandatory("path")
    current_ex_level_str, path = path_id.split(":", 1)
    current_ex_level = int(current_ex_level_str)

    if user.bi_expansion_level != current_ex_level:
        user.set_tree_states("bi", {})
    user.set_tree_state("bi", path, request.var("state") == "open")
    user.save_tree_states()

    user.bi_expansion_level = current_ex_level


def ajax_render_tree():
    aggr_group = request.get_str_input("group")
    aggr_title = request.get_str_input("title")
    omit_root = bool(request.var("omit_root"))
    only_problems = bool(request.var("only_problems"))

    rows = []
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    aggregation_id = request.get_str_input_mandatory("aggregation_id")
    bi_aggregation_filter = BIAggregationFilter(
        [],
        [],
        [aggregation_id],
        [aggr_title] if aggr_title is not None else [],
        [aggr_group] if aggr_group is not None else [],
        [],
    )
    rows = bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)

    # TODO: Cleanup the renderer to use a class registry for lookup
    renderer_class_name = request.var("renderer")
    if renderer_class_name == "FoldableTreeRendererTree":
        renderer_cls: type[ABCFoldableTreeRenderer] = FoldableTreeRendererTree
    elif renderer_class_name == "FoldableTreeRendererBoxes":
        renderer_cls = FoldableTreeRendererBoxes
    elif renderer_class_name == "FoldableTreeRendererBottomUp":
        renderer_cls = FoldableTreeRendererBottomUp
    elif renderer_class_name == "FoldableTreeRendererTopDown":
        renderer_cls = FoldableTreeRendererTopDown
    else:
        raise NotImplementedError()

    renderer = renderer_cls(
        rows[0],
        omit_root=omit_root,
        expansion_level=user.bi_expansion_level,
        only_problems=only_problems,
        lazy=False,
    )
    html.write_html(renderer.render())


def find_all_leaves(  # type:ignore[no-untyped-def]
    node,
) -> list[tuple[str | None, HostName, ServiceName | None]]:
    # leaf node
    if node["type"] == 1:
        site, host = node["host"]
        return [(site, host, node.get("service"))]

    # rule node
    if node["type"] == 2:
        entries: list[Any] = []
        for n in node["nodes"]:
            entries += find_all_leaves(n)
        return entries

    # place holders
    return []


@request_memoize()
def get_cached_bi_packs() -> BIAggregationPacks:
    bi_packs = BIAggregationPacks(BIManager.bi_configuration_file())
    bi_packs.load_config()
    return bi_packs
