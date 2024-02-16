#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success


class TestValueSpecPercentage:
    def test_validate(self) -> None:
        expect_validate_failure(vs.Percentage(), 105.0)
        expect_validate_success(vs.Percentage(), 101.0)
        expect_validate_failure(vs.Percentage(), -10.0)
        expect_validate_failure(vs.Percentage(), 10)
        expect_validate_success(vs.Percentage(allow_int=True), 10)
        expect_validate_failure(vs.Percentage(allow_int=True), "10")  # type: ignore[misc]

    def test_value_to_html(self) -> None:
        assert vs.Percentage().value_to_html(100) == "100%"
        assert vs.Percentage().value_to_html(10) == "10%"
        assert vs.Percentage().value_to_html(1) == "1%"
        assert vs.Percentage().value_to_html(0.1) == "0.1%"
        assert vs.Percentage().value_to_html(0.01) == "0.01%"
        assert vs.Percentage().value_to_html(-0.01) == "-0.01%"
