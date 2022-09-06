#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Any, Dict, Final

import cmk.gui.visuals as visuals
from cmk.gui.data_source import data_source_registry
from cmk.gui.hooks import request_memoize
from cmk.gui.type_defs import AllViewSpecs, PainterSpec, PermittedViewSpecs, ViewName, ViewSpec

# TODO: Refactor to plugin_registries
multisite_builtin_views: Dict = {}


def _internal_view_to_runtime_view(raw_view: dict[str, Any]) -> ViewSpec:
    return painter_specs_to_runtime_format(raw_view)


def painter_specs_to_runtime_format(view: ViewSpec) -> ViewSpec:
    if "painters" in view:
        view["painters"] = [PainterSpec.from_raw(v) for v in view["painters"]]
    if "group_painters" in view:
        view["group_painters"] = [PainterSpec.from_raw(v) for v in view["group_painters"]]
    return view


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
        # Skip views which do not belong to known datasources
        return visuals.load(
            "views",
            multisite_builtin_views,
            _internal_view_to_runtime_view,
            skip_func=lambda v: v["datasource"] not in data_source_registry,
        )

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
