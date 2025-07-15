#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user

from cmk.bi.computer import BIAggregationFilter

from .bi_manager import BIManager
from .foldable_tree_renderer import (
    ABCFoldableTreeRenderer,
    FoldableTreeRendererBottomUp,
    FoldableTreeRendererBoxes,
    FoldableTreeRendererTopDown,
    FoldableTreeRendererTree,
)
from .helpers import get_state_assumption_key
from .view import convert_tree_to_frozen_diff_tree


def ajax_set_assumption(config: Config) -> None:
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


def ajax_save_treestate(config: Config) -> None:
    path_id = request.get_str_input_mandatory("path")
    current_ex_level_str, path = path_id.split(":", 1)
    current_ex_level = int(current_ex_level_str)

    if user.bi_expansion_level != current_ex_level:
        user.set_tree_states("bi", {})
    user.set_tree_state("bi", path, request.var("state") == "open")
    user.save_tree_states()

    user.bi_expansion_level = current_ex_level


def ajax_render_tree(config: Config) -> None:
    aggr_group = request.get_str_input("group")
    aggr_title = request.get_str_input("title")
    omit_root = bool(request.var("omit_root"))
    only_problems = bool(request.var("only_problems"))
    show_frozen_difference = bool(request.var("show_frozen_difference"))

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
    row = bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)[0]
    if show_frozen_difference:
        row, _aggregations_are_equal = convert_tree_to_frozen_diff_tree(row)

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
        row,
        omit_root=omit_root,
        expansion_level=user.bi_expansion_level,
        only_problems=only_problems,
        lazy=False,
        show_frozen_difference=show_frozen_difference,
    )
    html.write_html(renderer.render())
