#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestCheckbox:
    def test_validate(self) -> None:
        expect_validate_success(vs.Checkbox(), True)
        expect_validate_success(vs.Checkbox(), False)
        expect_validate_failure(vs.Checkbox(), "abc")  # type: ignore[misc]
        expect_validate_failure(vs.Checkbox(), 123)  # type: ignore[misc]

    def test_canonical_value(self) -> None:
        assert vs.Checkbox().canonical_value() is False

    def test_mask(self) -> None:
        assert vs.Checkbox().mask(False) is False
        assert vs.Checkbox().mask(True) is True

    def test_value_to_html(self) -> None:
        assert vs.Checkbox().value_to_html(True) == "on"
        assert vs.Checkbox().value_to_html(False) == "off"
        assert vs.Checkbox(true_label="an").value_to_html(True) == "an"
        assert vs.Checkbox(false_label="aus").value_to_html(False) == "aus"

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(checkbox="on"):
            assert vs.Checkbox().from_html_vars("checkbox") is True
        assert vs.Checkbox().from_html_vars("checkbox") is False

    def test_json(self) -> None:
        assert vs.Checkbox().value_to_json(True) is True
        assert vs.Checkbox().value_to_json(False) is False
        assert vs.Checkbox().value_from_json(True) is True
        assert vs.Checkbox().value_from_json(False) is False
