#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the shipped built-in maps.

Every built-in map is served through the strict REST ``show``/``list`` path and
registered with the daemon, so its stored payload must be a complete, valid
map — a minimally-stored spec (relying on daemon defaults) would crash those
endpoints. This pins that each shipped map validates against both the daemon's
and the REST API's map model.
"""

import pytest

from cmk.maps.backend.schemas.map import MapConfig as DaemonMapConfig
from cmk.maps.gui.builtin_maps import builtin_map_configs
from cmk.maps.rest_api.utils import map_from_spec, spec_from_map

_EXPECTED_BUILTINS = {
    "all_hosts",
    "service_problems",
    "infrastructure",
    "monitoring_folders",
    "noc_wall",
}


def test_ships_the_expected_builtin_maps(request_context: None) -> None:  # noqa: ARG001
    assert set(builtin_map_configs()) == _EXPECTED_BUILTINS


def test_builtin_maps_are_public_and_readonly(request_context: None) -> None:  # noqa: ARG001
    for cfg in builtin_map_configs().values():
        assert cfg.public is True
        assert cfg.map_spec["readonly"] is True


@pytest.mark.parametrize("name", sorted(_EXPECTED_BUILTINS))
def test_builtin_map_validates_against_both_models(request_context: None, name: str) -> None:  # noqa: ARG001
    spec = dict(builtin_map_configs()[name].map_spec)
    # Daemon model is the shape source of truth (applied to every served map).
    dense = DaemonMapConfig.model_validate(spec).model_dump(mode="json")
    # The strict REST model (drives show/list and the generated TS types) must
    # group it cleanly and round-trip back to a valid daemon map.
    rest_obj = map_from_spec(dense)
    DaemonMapConfig.model_validate(spec_from_map(rest_obj))
