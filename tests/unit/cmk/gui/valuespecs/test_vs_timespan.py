#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.valuespec import TimeSpan

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestValueSpecTimeSpan:
    def test_validate(self) -> None:
        expect_validate_failure(TimeSpan(), 100)
        expect_validate_success(TimeSpan(), 100.0)
        expect_validate_failure(TimeSpan(), "smth")  # type: ignore[misc]
        expect_validate_failure(TimeSpan(minvalue=300.0), 100.0)
        expect_validate_failure(TimeSpan(maxvalue=300.0), 400.0)
        expect_validate_success(TimeSpan(minvalue=100.0, maxvalue=300.0), 200.0)

    def test_default(self) -> None:
        assert TimeSpan().default_value() == 0.0
        assert TimeSpan(minvalue=100.0).default_value() == 100.0
        assert TimeSpan().canonical_value() == 0.0
        assert TimeSpan(minvalue=100.0).canonical_value() == 100.0

    def test_json(self) -> None:
        assert TimeSpan().value_from_json(10.0) == 10.0
        assert TimeSpan().value_to_json(10.0) == 10.0

    def test_mask(self) -> None:
        assert TimeSpan().mask(20.0) == 20.0

    def test_value_to_html(self) -> None:
        assert TimeSpan().value_to_html(0) == "no time (zero)"
        assert TimeSpan().value_to_html(10) == "10 seconds"
        assert TimeSpan().value_to_html(9 * 60) == "9 minutes"
        assert TimeSpan().value_to_html(8 * 60 * 60) == "8 hours"
        assert TimeSpan().value_to_html(7 * 60 * 60 * 24) == "7 days"
        assert TimeSpan().value_to_html(7 * 60 * 60 * 24 + 10) == "7 days 10 seconds"
        assert TimeSpan().value_to_html(7 * 60 * 60 * 24 + 10.213) == "7 days 10 seconds 213 ms"

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(
            v_days="1", v_hours="2", v_minutes="3", v_seconds="4", v_milliseconds="345"
        ):
            result = 1 * (24 * 60 * 60) + 2 * (60 * 60) + 3 * (60) + 4.345 * (1)
            assert TimeSpan().from_html_vars("v") == result
