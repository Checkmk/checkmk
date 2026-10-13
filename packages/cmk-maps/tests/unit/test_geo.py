#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon host geo resolver (cmk.maps.shared.geo)."""

from cmk.maps.shared.geo import resolve_host_coords


def test_prefers_maps_labels() -> None:
    coords = resolve_host_coords(
        {"maps_lat": "51.0", "maps_lng": "10.0"}, {"LAT": "1", "LONG": "2"}
    )
    assert coords == (51.0, 10.0)


def test_falls_back_to_legacy_custom_vars() -> None:
    assert resolve_host_coords({}, {"LAT": "48.1", "LONG": "11.5"}) == (48.1, 11.5)


def test_falls_back_when_label_is_unparseable() -> None:
    # A present-but-garbage label must not shadow usable legacy coords.
    assert resolve_host_coords({"maps_lat": "x", "maps_lng": "y"}, {"LAT": "1", "LONG": "2"}) == (
        1.0,
        2.0,
    )


def test_none_when_nothing_usable() -> None:
    assert resolve_host_coords({}, {}) is None
    assert resolve_host_coords({"maps_lat": "x", "maps_lng": "y"}, {}) is None
    assert resolve_host_coords({"maps_lat": "51.0"}, {}) is None
