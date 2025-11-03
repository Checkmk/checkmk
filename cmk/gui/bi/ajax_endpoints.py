#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import dataclasses
from typing import Self

from cmk.bi.computer import BIAggregationFilter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext

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


@dataclasses.dataclass(frozen=True)
class _RequestVarsAssumption:
    site: str | None
    host: str | None
    service: str | None
    state: str | None

    @classmethod
    def build(cls, request: Request) -> Self:
        return cls(
            site=request.get_str_input("site"),
            host=request.get_str_input("host"),
            service=request.get_str_input("service"),
            state=request.var("state"),
        )


def ajax_set_assumption(ctx: PageContext) -> None:
    match (reqvars := _RequestVarsAssumption.build(ctx.request)).state:
        case "none":
            key = get_state_assumption_key(reqvars.site, reqvars.host, reqvars.service)
            del user.bi_assumptions[key]
        case str(state):
            key = get_state_assumption_key(reqvars.site, reqvars.host, reqvars.service)
            user.bi_assumptions[key] = int(state)
        case None:
            raise Exception("ajax_set_assumption: state is None")

    user.save_bi_assumptions()


@dataclasses.dataclass(frozen=True)
class _RequestVarsTreeState:
    path_id: str
    path: str
    current_ex_level: int
    is_open: bool

    @classmethod
    def build(cls, request: Request) -> Self:
        path_id = request.get_str_input_mandatory("path")
        current_ex_level, path = path_id.split(":", 1)

        return cls(
            path_id=path_id,
            path=path,
            current_ex_level=int(current_ex_level),
            is_open=request.var("state") == "open",
        )


def ajax_save_treestate(ctx: PageContext) -> None:
    reqvars = _RequestVarsTreeState.build(ctx.request)

    if user.bi_expansion_level != reqvars.current_ex_level:
        user.set_tree_states("bi", {})
    user.set_tree_state("bi", reqvars.path, reqvars.is_open)
    user.save_tree_states()

    user.bi_expansion_level = reqvars.current_ex_level


@dataclasses.dataclass(frozen=True)
class _RequestVarsTree:
    aggr_id: str
    aggr_group: str | None
    aggr_title: str | None
    renderer_name: str | None
    omit_root: bool
    only_problems: bool
    show_frozen_difference: bool

    @classmethod
    def build(cls, request: Request) -> Self:
        return cls(
            aggr_id=request.get_str_input_mandatory("aggregation_id"),
            aggr_group=request.get_str_input("group"),
            aggr_title=request.get_str_input("title"),
            renderer_name=request.var("renderer"),
            omit_root=bool(request.var("omit_root")),
            only_problems=bool(request.var("only_problems")),
            show_frozen_difference=bool(request.var("show_frozen_difference")),
        )


def ajax_render_tree(ctx: PageContext) -> None:
    reqvars = _RequestVarsTree.build(ctx.request)

    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    bi_aggregation_filter = BIAggregationFilter(
        [],
        [],
        [reqvars.aggr_id],
        [reqvars.aggr_title] if reqvars.aggr_title is not None else [],
        [reqvars.aggr_group] if reqvars.aggr_group is not None else [],
        [],
    )
    row = bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)[0]
    if reqvars.show_frozen_difference:
        row, _aggregations_are_equal = convert_tree_to_frozen_diff_tree(row)

    # TODO: Cleanup the renderer to use a class registry for lookup
    match reqvars.renderer_name:
        case "FoldableTreeRendererTree":
            renderer_cls: type[ABCFoldableTreeRenderer] = FoldableTreeRendererTree
        case "FoldableTreeRendererBoxes":
            renderer_cls = FoldableTreeRendererBoxes
        case "FoldableTreeRendererBottomUp":
            renderer_cls = FoldableTreeRendererBottomUp
        case "FoldableTreeRendererTopDown":
            renderer_cls = FoldableTreeRendererTopDown
        case _:
            raise NotImplementedError()

    renderer = renderer_cls(
        row,
        omit_root=reqvars.omit_root,
        expansion_level=user.bi_expansion_level,
        only_problems=reqvars.only_problems,
        lazy=False,
        show_frozen_difference=reqvars.show_frozen_difference,
    )
    html.write_html(renderer.render())
