#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Sequence

from cmk.gui.config import Config
from cmk.gui.painter.painters import (
    add_docker_nodes,
    add_max_long_output_sizes,
)
from cmk.gui.type_defs import ColumnSpec, SorterSpec, ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views._row_extenders import _needed_row_extenders
from cmk.gui.views.inventory._painters import add_sites_of_same_named_hosts
from cmk.gui.views.store import multisite_builtin_views
from cmk.web.utils.request_cache import RequestCache
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


def _view(view_name: str, spec: ViewSpec) -> View:
    return View(
        view_name,
        spec,
        spec.get("context", {}),
        make_painter_context(UserPermissions({}, {}, {}, [])),
        RequestCache(Config()),
    )


def _view_of_services(painters: Sequence[ColumnSpec], sorters: Sequence[SorterSpec]) -> View:
    spec: ViewSpec = copy.deepcopy(multisite_builtin_views["allservices"])
    spec["group_painters"] = []
    spec["painters"] = list(painters)
    spec["sorters"] = list(sorters)
    return _view("allservices", spec)


def test_a_column_tooltip_needs_the_row_extender_of_its_painter() -> None:
    view = _view_of_services(
        [ColumnSpec(name="service_description", tooltip="svc_long_plugin_output")], []
    )
    assert _needed_row_extenders(view) == [add_max_long_output_sizes]


def test_a_row_extender_needed_by_several_columns_is_needed_once() -> None:
    view = _view_of_services(
        [ColumnSpec(name="svc_long_plugin_output"), ColumnSpec(name="svc_long_plugin_output")], []
    )
    assert _needed_row_extenders(view) == [add_max_long_output_sizes]


def test_a_sorter_needs_its_row_extender() -> None:
    view = _view_of_services([], [SorterSpec(sorter="host_docker_node", negate=False)])
    assert _needed_row_extenders(view) == [add_docker_nodes]


def test_the_inventory_history_needs_the_sites_of_same_named_hosts() -> None:
    spec: ViewSpec = copy.deepcopy(multisite_builtin_views["inv_host_history"])
    assert _needed_row_extenders(_view("inv_host_history", spec)) == [add_sites_of_same_named_hosts]
