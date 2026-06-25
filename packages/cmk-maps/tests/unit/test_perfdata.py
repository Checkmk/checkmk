#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon perf_data parser (cmk.maps.shared.perfdata)."""

from cmk.maps.shared.perfdata import parse_perf_metrics


def test_parses_label_and_unit() -> None:
    assert parse_perf_metrics("rta=5ms;100;200 pl=0%;5;10") == [
        {"label": "rta", "unit": "ms"},
        {"label": "pl", "unit": "%"},
    ]


def test_keeps_quoted_labels_with_spaces() -> None:
    # A quoted label with a space must stay one metric, not two.
    assert parse_perf_metrics("'disk usage'=50GB") == [{"label": "disk usage", "unit": "GB"}]


def test_keeps_quoted_label_containing_equals() -> None:
    # A quoted label may itself contain '='; splitting on the first '=' would
    # tear it into "a" and drop the unit.
    assert parse_perf_metrics("'a=b'=5ms") == [{"label": "a=b", "unit": "ms"}]


def test_empty_perf_data() -> None:
    assert parse_perf_metrics("") == []


def test_missing_unit_is_empty_string() -> None:
    assert parse_perf_metrics("count=42") == [{"label": "count", "unit": ""}]
