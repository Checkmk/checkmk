#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry
from cmk.web.utils.request_cache import RequestCache


def _expected_visual_types() -> Mapping[str, Mapping[str, str | bool | None]]:
    return {
        "dashboards": {
            "add_visual_handler": "popup_add_dashlet",
            "ident_attr": "name",
            "multicontext_links": False,
            "plural_title": "dashboards",
            "show_url": "dashboard.py",
            "title": "dashboard",
        },
        "views": {
            "add_visual_handler": None,
            "ident_attr": "view_name",
            "multicontext_links": False,
            "plural_title": "views",
            "show_url": "view.py",
            "title": "view",
        },
    }


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_visual_types() -> None:
    assert sorted(visual_type_registry.keys()) == sorted(_expected_visual_types().keys())


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_visual_type_attributes() -> None:
    for ident, plugin_class in visual_type_registry.items():
        plugin = plugin_class()
        spec = _expected_visual_types()[ident]

        # TODO: Add tests for the results of these functions
        # assert plugin.add_visual_handler == spec["add_visual_handler"]
        assert plugin.ident_attr == spec["ident_attr"]
        assert plugin.multicontext_links == spec["multicontext_links"]
        assert plugin.plural_title == spec["plural_title"]
        assert plugin.show_url == spec["show_url"]
        assert plugin.title == spec["title"]


@pytest.mark.usefixtures("load_gui_plugins")
def test_get_context_specs_no_info_limit() -> None:
    result = visuals.get_context_specs(
        ["host"], list(visual_info_registry.keys()), RequestCache(Config())
    )
    expected = {
        "aggr",
        "aggr_group",
        "comment",
        "crash",
        "discovery",
        "downtime",
        "event",
        "history",
        "host",
        "hostgroup",
        "log",
        "service",
        "servicegroup",
    }

    # depending on the tests sandbox, there might be results created from inventory_ui plugins
    assert {r for r, *_ in result if not r.startswith("inv")} == expected
