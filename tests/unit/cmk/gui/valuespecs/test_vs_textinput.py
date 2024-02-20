#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestValueSpecTextInput:
    def test_validate(self) -> None:
        expect_validate_success(vs.TextInput(), "smth")
        expect_validate_success(vs.TextInput(), "")

        expect_validate_failure(vs.TextInput(forbidden_chars="s"), "smth")
        expect_validate_failure(vs.TextInput(allow_empty=False), " ")
        expect_validate_failure(vs.TextInput(allow_empty=False), "")
        expect_validate_success(vs.TextInput(allow_empty=False, strip=False), " ")

        expect_validate_success(vs.TextInput(regex="[1-3]"), "3")
        expect_validate_success(vs.TextInput(regex="[1-3]"), "33")
        expect_validate_failure(vs.TextInput(regex="^[1-3]$"), "33")
        expect_validate_failure(vs.TextInput(regex="[1-3]"), "4")
        with pytest.raises(MKUserError, match="don't"):
            expect_validate_success(
                vs.TextInput(regex="[1-3]", regex_error="don't, just don't"), "4"
            )

        expect_validate_success(vs.TextInput(minlen=3), "123")
        expect_validate_failure(vs.TextInput(minlen=3), "12")
        expect_validate_success(vs.TextInput(maxlen=3), "123")
        expect_validate_failure(vs.TextInput(maxlen=3), "1234")

    def test_html_vars(self, request_context: None) -> None:
        with request_var(dr="who"):
            assert vs.TextInput().from_html_vars("dr") == "who"

        with request_var(dr="who "):
            assert vs.TextInput().from_html_vars("dr") == "who"
            assert vs.TextInput(strip=False).from_html_vars("dr") == "who "

    def test_value_to_html(self) -> None:
        assert vs.TextInput().value_to_html("smth") == "smth"
        assert vs.TextInput().value_to_html("") == ""
        assert vs.TextInput(empty_text="empty").value_to_html("") == "empty"

    def test_default_value(self) -> None:
        assert vs.TextInput().canonical_value() == ""
        assert vs.TextInput(default_value="a").canonical_value() == ""
        assert vs.TextInput(default_value="a").default_value() == "a"
        assert vs.TextInput(default_value=lambda: "a").default_value() == "a"

    def test_mask(self) -> None:
        assert vs.TextInput().mask("tape") == "tape"

    def test_json(self) -> None:
        assert vs.TextInput().value_from_json(vs.TextInput().value_to_json("b")) == "b"
        assert vs.TextInput().value_from_json("c") == "c"
        assert vs.TextInput().value_to_json("d") == "d"

    def test_transform_value(self) -> None:
        valuespec = vs.TextInput()
        assert valuespec.transform_value("lala") == "lala"
        assert valuespec.transform_value("AAA") == "AAA"
