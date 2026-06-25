#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon dyngroup-filter allowlist (cmk.maps.shared.filters)."""

import pytest

from cmk.maps.shared.filters import normalize_object_filter


def test_appends_trailing_newline() -> None:
    # NagVis stores single-filter dyngroups without a trailing separator.
    assert normalize_object_filter("Filter: host_name ~ ^web") == "Filter: host_name ~ ^web\n"


def test_expands_literal_backslash_n() -> None:
    assert normalize_object_filter("Filter: a\\nFilter: b") == "Filter: a\nFilter: b\n"


def test_keeps_a_literal_backslash_r_inside_one_line() -> None:
    # Only ``\n`` is un-escaped (NagVis' own separator). A literal backslash-r is
    # two harmless characters for Livestatus, so it must not be mistaken for a CR
    # and split a line apart.
    assert normalize_object_filter("Filter: a\\rb") == "Filter: a\\rb\n"


def test_rejects_control_characters() -> None:
    # A NUL survives both splitlines() and the ``.+`` of the header regex, so it
    # would otherwise reach Livestatus inside an otherwise well-formed line.
    with pytest.raises(ValueError):
        normalize_object_filter("Filter: a\x00Stats: state = 0")


def test_accepts_combinator_headers() -> None:
    assert (
        normalize_object_filter("Filter: a\\nFilter: b\\nOr: 2") == "Filter: a\nFilter: b\nOr: 2\n"
    )


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("Filter: a\\nStats: state = 0", id="stats"),
        pytest.param("Filter: a\\nColumns: name address", id="columns"),
        pytest.param("Filter: a\\nOutputFormat: python", id="outputformat"),
        pytest.param("Filter: a\\nGET hosts", id="get"),
        pytest.param("Filter: a\\nAuthUser: admin", id="authuser"),
        # Livestatus splits headers on newlines, and str.splitlines() splits on
        # more than \n — every one of those separators must be seen, or a smuggled
        # header would ride inside what looks like a single Filter: line.
        pytest.param("Filter: a\rStats: state = 0", id="carriage-return"),
        pytest.param("Filter: a\r\nStats: state = 0", id="crlf"),
        pytest.param("Filter: a\u2028Stats: state = 0", id="line-separator"),
        pytest.param("Filter: a\x0bStats: state = 0", id="vertical-tab"),
        pytest.param("Filter: a\x0cStats: state = 0", id="form-feed"),
        pytest.param("Filter: a\x1cStats: state = 0", id="file-separator"),
        pytest.param("Stats: state = 0", id="bare-stats"),
        pytest.param("GET hosts", id="bare-get"),
        pytest.param("", id="empty"),
    ],
)
def test_rejects_injected_headers(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_object_filter(value)
