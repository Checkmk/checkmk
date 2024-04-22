#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestValueSpecLegacyDataSize:
    # this is based on the integer tests
    def test_validate(self) -> None:
        expect_validate_failure(vs.LegacyDataSize(), "asd")  # type: ignore[misc]
        expect_validate_success(vs.LegacyDataSize(), 128)

    def test_default_value(self) -> None:
        assert vs.LegacyDataSize().default_value() == 0
        assert vs.LegacyDataSize(default_value=99).default_value() == 99
        assert vs.LegacyDataSize(default_value=lambda: 77).default_value() == 77

    def test_canonical_value(self) -> None:
        assert vs.LegacyDataSize().canonical_value() == 0
        assert vs.LegacyDataSize(default_value=99).canonical_value() == 0
        assert vs.LegacyDataSize(default_value=lambda: 77).canonical_value() == 0

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(integer_size="123", integer_unit=str(1024**3)):
            assert vs.LegacyDataSize().from_html_vars("integer") == 123 * 1024**3

        with request_var(integer_size="0.5", integer_unit=str(1024**3)):
            assert vs.LegacyDataSize().from_html_vars("integer") == int(0.5 * 1024**3)

        # see last entry in test_value_to_html
        with request_var(integer_size="9.313225746154785e-10", integer_unit=str(1024**4)):
            assert vs.LegacyDataSize().from_html_vars("integer") == 1024

    def test_value_to_html(self) -> None:
        assert vs.LegacyDataSize().value_to_html(123) == "123 Byte"
        assert vs.LegacyDataSize().value_to_html(1002003) == "1002003 Byte"
        # input only allows input in TiB but we found 1KiB as Value:
        assert (
            vs.LegacyDataSize(units=[vs.LegacyBinaryUnit.TiB]).value_to_html(1024)
            == "9.313225746154785e-10 TiB"
        )

    def test_json(self) -> None:
        assert vs.LegacyDataSize().value_from_json(vs.LegacyDataSize().value_to_json(10)) == 10
        assert vs.LegacyDataSize().value_from_json(11.0) == 11
        assert vs.LegacyDataSize().value_to_json(12) == 12

    def test_mask(self) -> None:
        assert vs.LegacyDataSize().mask(13) == 13
