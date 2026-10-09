#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon host geo resolver (cmk.maps.shared.geo)."""

import pytest

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


@pytest.mark.parametrize(
    ("lat", "lng", "expected"),
    [
        pytest.param("48.1", "-0.5", (48.1, -0.5), id="decimal"),
        pytest.param("90", "-180", (90.0, -180.0), id="bounds"),
        pytest.param(" 48.1 ", "11.5", (48.1, 11.5), id="padded"),
        pytest.param("nan", "11.5", None, id="nan"),
        pytest.param("48.1", "inf", None, id="inf"),
        pytest.param("48_1", "11.5", None, id="underscore"),
        pytest.param("48,1", "11.5", None, id="comma"),
        pytest.param("1e3", "11.5", None, id="exponent"),
        pytest.param("95", "11.5", None, id="lat-out-of-range"),
        pytest.param("48.1", "200", None, id="lng-out-of-range"),
        pytest.param("", "11.5", None, id="empty"),
    ],
)
def test_accepts_only_decimal_degrees_in_range(
    lat: str, lng: str, expected: tuple[float, float] | None
) -> None:
    assert resolve_host_coords({"maps_lat": lat, "maps_lng": lng}, {}) == expected


def test_falls_back_when_label_is_out_of_range() -> None:
    assert resolve_host_coords(
        {"maps_lat": "95", "maps_lng": "10"}, {"LAT": "48.1", "LONG": "11.5"}
    ) == (48.1, 11.5)
