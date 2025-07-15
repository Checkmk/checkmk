#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Any, Final

import cmk.ccc.version as cmk_version

from cmk.utils import paths

from cmk.gui import visuals
from cmk.gui.config import active_config
from cmk.gui.data_source import data_source_registry
from cmk.gui.hooks import request_memoize
from cmk.gui.type_defs import (
    AllViewSpecs,
    ColumnSpec,
    PermittedViewSpecs,
    SorterSpec,
    ViewName,
    ViewSpec,
)

from .builtin_views import builtin_view_extender_registry

# TODO: Refactor to plugin_registries
multisite_builtin_views: dict[ViewName, ViewSpec] = {}


def internal_view_to_runtime_view(raw_view: dict[str, Any]) -> ViewSpec:
    # Need to assume that we are right for now. We will have to introduce parsing there to do a real
    # conversion in one of the following typing steps.
    raw_view.setdefault("packaged", False)
    raw_view.setdefault("main_menu_search_terms", [])
    return _sorter_specs_to_runtime_format(_column_specs_to_runtime_format(raw_view))  # type: ignore[arg-type]


def _column_specs_to_runtime_format(view: dict[str, Any]) -> ViewSpec:
    if "painters" in view:
        view["painters"] = [ColumnSpec.from_raw(v) for v in view["painters"]]
    if "group_painters" in view:
        view["group_painters"] = [ColumnSpec.from_raw(v) for v in view["group_painters"]]
    # Need to assume that we are right for now. We will have to introduce parsing there to do a real
    # conversion in one of the following typing steps.
    return view  # type: ignore[return-value]


def _sorter_specs_to_runtime_format(view: dict[str, Any]) -> ViewSpec:
    if "sorters" in view:
        view["sorters"] = [SorterSpec(*s) for s in view["sorters"]]
    # Need to assume that we are right for now. We will have to introduce parsing there to do a real
    # conversion in one of the following typing steps.
    return view  # type: ignore[return-value]


class ViewStore:
    @classmethod
    @request_memoize()
    def get_instance(cls) -> ViewStore:
        """Return the request bound instance"""
        return cls()

    def __init__(self) -> None:
        self.all: Final = ViewStore._load_all_views()
        self.permitted: Final = ViewStore._load_permitted_views(self.all)

    @staticmethod
    def _load_all_views() -> AllViewSpecs:
        """Loads all view definitions from disk and returns them"""
        return {
            k: v
            for k, v in visuals.load(
                "views",
                builtin_view_extender_registry[cmk_version.edition(paths.omd_root).short].callable(
                    multisite_builtin_views, data_source_registry, active_config
                ),
                internal_view_to_runtime_view,
            ).items()
            if v["datasource"] in data_source_registry
        }

    @staticmethod
    def _load_permitted_views(all_views: AllViewSpecs) -> PermittedViewSpecs:
        """Returns all view defitions that a user is allowed to use"""
        return visuals.available("views", all_views)


def get_all_views() -> AllViewSpecs:
    return ViewStore.get_instance().all


def get_permitted_views() -> PermittedViewSpecs:
    return ViewStore.get_instance().permitted


def get_view_by_name(view_name: ViewName) -> ViewSpec:
    return get_permitted_views()[view_name]
