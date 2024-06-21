#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestValueSpecAge:
    def test_validate(self) -> None:
        expect_validate_success(vs.Age(), 100)
        expect_validate_failure(vs.Age(), "smth")  # type: ignore[misc]
        expect_validate_failure(vs.Age(minvalue=300), 100)
        expect_validate_failure(vs.Age(maxvalue=300), 400)
        expect_validate_success(vs.Age(minvalue=100, maxvalue=300), 200)

    def test_default(self) -> None:
        assert vs.Age().default_value() == 0
        assert vs.Age(minvalue=100).default_value() == 100
        assert vs.Age().canonical_value() == 0
        assert vs.Age(minvalue=100).canonical_value() == 100

    def test_json(self) -> None:
        assert vs.Age().value_from_json(10) == 10
        assert vs.Age().value_to_json(10) == 10

    def test_mask(self) -> None:
        assert vs.Age().mask(20) == 20

    def test_value_to_html(self) -> None:
        assert vs.Age().value_to_html(0) == "no time"
        assert vs.Age().value_to_html(10) == "10 seconds"
        assert vs.Age().value_to_html(9 * 60) == "9 minutes"
        assert vs.Age().value_to_html(8 * 60 * 60) == "8 hours"
        assert vs.Age().value_to_html(7 * 60 * 60 * 24) == "7 days"
        assert vs.Age().value_to_html(7 * 60 * 60 * 24 + 10) == "7 days 10 seconds"

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(v_days="1", v_hours="2", v_minutes="3", v_seconds="4"):
            result = 1 * (24 * 60 * 60) + 2 * (60 * 60) + 3 * (60) + 4 * (1)
            assert vs.Age().from_html_vars("v") == result
