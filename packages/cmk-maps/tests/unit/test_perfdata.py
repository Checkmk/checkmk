#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pins the shared GUI↔daemon perf_data parser (cmk.maps.shared.perfdata)."""

import pytest

from cmk.maps.shared.perfdata import MAX_PERF_DATA_LENGTH, parse_perf_metrics


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


# The same vectors pin parsePerfData in cmk-frontend-vue/tests/maps/utils/perf.test.ts.
@pytest.mark.parametrize(
    "perf_data, expected",
    [
        ("a=b=5 ok=1", [("ok", "")]),
        ("'a=b'=5ms", [("a=b", "ms")]),
        ("''=1", []),
        ("rate=5B/s", [("rate", "B/s")]),
        ("temp=-3.5C;0;10", [("temp", "C")]),
        ("'unclosed a=1 'b c'=2", [("a", ""), ("b c", "")]),
        ("OK [check_cpu] load1=0.5", [("load1", "")]),
        ("x=.5 y=- z=abc", [("x", "")]),
    ],
)
def test_parses_the_shared_vectors(perf_data: str, expected: list[tuple[str, str]]) -> None:
    assert [(m["label"], m["unit"]) for m in parse_perf_metrics(perf_data)] == expected


def test_parses_a_long_part_without_a_metric() -> None:
    assert parse_perf_metrics("'" + "a" * (MAX_PERF_DATA_LENGTH - 1)) == []


def test_perf_data_past_the_limit_has_no_metrics() -> None:
    assert parse_perf_metrics("a=1 " * (MAX_PERF_DATA_LENGTH // 4 + 1)) == []
