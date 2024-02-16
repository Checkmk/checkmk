#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestValueSpecFloat:
    def test_validate(self) -> None:
        expect_validate_failure(vs.Float(), "asd")  # type: ignore[misc]
        expect_validate_failure(vs.Float(), 128)
        expect_validate_success(vs.Float(allow_int=True), 128)
        expect_validate_success(vs.Float(), 128.0)
        expect_validate_success(vs.Float(minvalue=10, maxvalue=300), 128.0)
        expect_validate_failure(vs.Float(minvalue=10, maxvalue=300), 333.0)
        expect_validate_failure(vs.Float(minvalue=10, maxvalue=300), 9.0)

    def test_default_value(self) -> None:
        assert vs.Float().default_value() == 0
        assert vs.Float(minvalue=10).default_value() == 10
        assert vs.Float(default_value=99).default_value() == 99
        assert vs.Float(default_value=99, minvalue=10).default_value() == 99
        assert vs.Float(default_value=lambda: 77).default_value() == 77
        assert vs.Float(default_value=lambda: 77, minvalue=10).default_value() == 77

    def test_canonical_value(self) -> None:
        assert vs.Float().canonical_value() == 0
        assert vs.Float(minvalue=10).canonical_value() == 10
        assert vs.Float(default_value=99).canonical_value() == 0
        assert vs.Float(default_value=99, minvalue=10).canonical_value() == 10
        assert vs.Float(default_value=lambda: 77).canonical_value() == 0
        assert vs.Float(default_value=lambda: 77, minvalue=10).canonical_value() == 10

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(integer="123"):
            assert vs.Float().from_html_vars("integer") == 123

        with request_var(integer="asd"):
            with pytest.raises(MKUserError):
                vs.Float().from_html_vars("integer")

    def test_value_to_html(self) -> None:
        assert vs.Float().value_to_html(123) == "123.0"
        assert vs.Float().value_to_html(None) == "0.0"  # type: ignore[arg-type]
        assert vs.Float(unit="unit").value_to_html(1002003) == "1002003.0 unit"
        assert vs.Float(unit="unit").value_to_html(0.999) == "0.999 unit"
        assert vs.Float().value_to_html(0.99) == "0.99"
        assert vs.Float().value_to_html(-0.999) == "-0.999"

    def test_json(self) -> None:
        assert vs.Float().value_from_json(11) == 11
        assert vs.Float().value_from_json(11.0) == 11.0
        assert vs.Float().value_to_json(12) == 12
        assert vs.Float().value_to_json(12.2) == 12.2

    def test_mask(self) -> None:
        assert vs.Float().mask(13) == 13
        assert vs.Float().mask(13.3) == 13.3
