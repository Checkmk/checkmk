#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestOptional:
    def test_validate(self) -> None:
        expect_validate_failure(vs.Optional(vs.Integer(minvalue=20)), "asd")  # type: ignore[misc]
        expect_validate_failure(vs.Optional(vs.Integer(minvalue=20)), 10)
        expect_validate_success(vs.Optional(vs.Integer(minvalue=20)), None)

    def test_mask(self) -> None:
        assert vs.Optional(vs.Password()).mask("password") == "******"
        assert vs.Optional(vs.Password()).mask(None) is None

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(o_use="smth", o_value="1"):
            assert vs.Optional(vs.Integer()).from_html_vars("o") == 1
            assert vs.Optional(vs.Integer(), negate=True).from_html_vars("o") is None
        with request_var(o_use="", o_value="1"):
            assert vs.Optional(vs.Integer()).from_html_vars("o") is None
            assert vs.Optional(vs.Integer(), negate=True).from_html_vars("o") == 1

    def test_canonical_value(self) -> None:
        assert vs.Optional(vs.Integer()).canonical_value() is None

    def test_json(self) -> None:
        assert vs.Optional(vs.TextInput()).value_from_json("a") == "a"
        assert vs.Optional(vs.TextInput()).value_to_json("b") == "b"
        assert vs.Optional(vs.TextInput()).value_from_json(None) is None
        assert vs.Optional(vs.TextInput()).value_to_json(None) is None

    def test_value_to_html(self) -> None:
        assert vs.Optional(vs.TextInput()).value_to_html(None) == "(unset)"
        assert vs.Optional(vs.TextInput(), none_label="smth").value_to_html(None) == "smth"
        assert vs.Optional(vs.TextInput()).value_to_html("value") == "value"
