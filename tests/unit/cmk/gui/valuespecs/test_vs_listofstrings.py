#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.valuespec as vs
from cmk.gui.utils.html import HTML

from .utils import expect_validate_failure, expect_validate_success, request_var


class TestListOfStrings:
    def test_canonical_value(self) -> None:
        assert not vs.ListOfStrings().canonical_value()

    def test_validate(self) -> None:
        expect_validate_success(vs.ListOfStrings(), ["1", "2"])
        expect_validate_success(vs.ListOfStrings(), [])
        expect_validate_failure(
            vs.ListOfStrings(allow_empty=False), [], match="Please specify at least one value"
        )
        expect_validate_failure(
            vs.ListOfStrings(allow_empty=False, empty_text="!!!"), [], match="^!!!$"
        )
        expect_validate_failure(
            vs.ListOfStrings(max_entries=1), ["1", "2"], match="You can specify at most 1 entries"
        )
        expect_validate_failure(  # type: ignore[misc]
            vs.ListOfStrings(), 123, match="Expected data type is list, but your type is int."
        )

    def test_value_to_html(self) -> None:
        assert vs.ListOfStrings().value_to_html(["1", "2"]) == HTML.without_escaping(
            "<table><tr><td>1</td></tr><tr><td>2</td></tr></table>"
        )
        assert vs.ListOfStrings(orientation="horizontal").value_to_html(["1", "2"]) == "1, 2"
        assert vs.ListOfStrings().value_to_html([]) == ""
        assert vs.ListOfStrings(empty_text="smth").value_to_html([]) == "smth"

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(l_0="a", l_4="b", l_9="", l_9999="z", l_smth="smth"):
            assert vs.ListOfStrings().from_html_vars("l") == ["a", "b", "z"]

    def test_mask(self) -> None:
        assert vs.ListOfStrings().mask(["1", "2"]) == ["1", "2"]
        assert vs.ListOfStrings(valuespec=vs.Password()).mask(["1", "2"]) == ["******", "******"]

    def test_value_to_json(self) -> None:
        assert vs.ListOfStrings().value_to_json(["1", "2"]) == ["1", "2"]

    def test_value_from_json(self) -> None:
        assert vs.ListOfStrings().value_from_json(["1", "2"]) == ["1", "2"]

    def test_allow_empty(self) -> None:
        assert vs.ListOfStrings(allow_empty=True).allow_empty() is True
        assert vs.ListOfStrings(allow_empty=False).allow_empty() is False
