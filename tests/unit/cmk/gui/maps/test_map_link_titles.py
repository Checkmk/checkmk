#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resolving the titles a map's links to other maps are captioned by.

The lookup is injected because only the GUI can decide whether the requesting
user may see a given map at all.
"""

from cmk.ccc.user import UserId
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.type_defs import map_config_from_spec, MapName
from cmk.maps.rest_api.utils import resolve_map_link_titles


def _page(name: str, alias: str | None = None) -> MapPage:
    spec: dict[str, object] = {"name": name, "view": {"type": "static"}}
    if alias is not None:
        spec["alias"] = alias
    return MapPage(map_config_from_spec(UserId("alice"), name, spec))


def _lookup(*pages: MapPage) -> dict[MapName, MapPage]:
    return {page.config.name: page for page in pages}


def _spec(*objects: dict[str, object]) -> dict[str, object]:
    return {"name": "overview", "view": {"type": "static"}, "objects": list(objects)}


def test_resolves_the_title_of_a_linked_map() -> None:
    visible = _lookup(_page("dc_2", "Datacenter 2"))
    spec = _spec({"id": "o1", "type": "map", "map_name": "dc_2"})

    assert resolve_map_link_titles(spec, visible.get) == {"dc_2": "Datacenter 2"}


def test_leaves_out_a_map_the_user_may_not_see() -> None:
    spec = _spec(
        {"id": "o1", "type": "map", "map_name": "dc_2"},
        {"id": "o2", "type": "map", "map_name": "private_map"},
    )

    titles = resolve_map_link_titles(spec, _lookup(_page("dc_2", "Datacenter 2")).get)

    assert titles == {"dc_2": "Datacenter 2"}


def test_falls_back_to_the_name_of_a_map_without_a_title() -> None:
    spec = _spec({"id": "o1", "type": "map", "map_name": "dc_2"})

    assert resolve_map_link_titles(spec, _lookup(_page("dc_2")).get) == {"dc_2": "dc_2"}


def test_resolves_a_map_linked_twice_only_once() -> None:
    looked_up: list[str] = []
    pages = _lookup(_page("dc_2", "Datacenter 2"))

    def lookup(name: MapName) -> MapPage | None:
        looked_up.append(name)
        return pages.get(name)

    spec = _spec(
        {"id": "o1", "type": "map", "map_name": "dc_2"},
        {"id": "o2", "type": "map", "map_name": "dc_2"},
    )

    assert resolve_map_link_titles(spec, lookup) == {"dc_2": "Datacenter 2"}
    assert looked_up == ["dc_2"]


def test_ignores_objects_that_are_not_map_links() -> None:
    spec = _spec(
        {"id": "o1", "type": "host", "host_name": "db01"},
        # A link still being placed has no target yet.
        {"id": "o2", "type": "map", "map_name": ""},
        {"id": "o3", "type": "map"},
    )

    assert resolve_map_link_titles(spec, _lookup(_page("dc_2", "Datacenter 2")).get) == {}


def test_tolerates_a_spec_without_objects() -> None:
    assert resolve_map_link_titles({"name": "overview"}, _lookup().get) == {}
