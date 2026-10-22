#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs
from tests.unit.cmk.gui.compare_html import ts_function_call

from .utils import (
    expect_validate_failure,
    expect_validate_success,
    render_input,
    request_var,
)


class TestOptionalDropdownChoice:
    def test_validate(self) -> None:
        valuespec = vs.OptionalDropdownChoice[str](
            explicit=vs.TextInput(), choices=[("id_a", "title_a"), ("id_b", "title_b")]
        )
        valuespec_max_len = vs.OptionalDropdownChoice[str](
            explicit=vs.TextInput(maxlen=2), choices=[("id_a", "title_a"), ("id_b", "title_b")]
        )
        expect_validate_success(
            valuespec,
            "smth",
        )
        expect_validate_success(
            valuespec,
            "id_a",
        )
        expect_validate_failure(
            valuespec_max_len,
            "very_very_long",
        )
        expect_validate_success(
            valuespec_max_len,
            "id_b",
        )

    @pytest.mark.usefixtures("request_context")
    def test_from_html_vars(self) -> None:
        valuespec = vs.OptionalDropdownChoice[str](
            explicit=vs.TextInput(), choices=[("id_a", "title_a"), ("id_b", "title_b")]
        )
        with request_var(od="0"):
            assert valuespec.from_html_vars("od") == "id_a"
        with request_var(od="other", od_ex="smth"):
            assert valuespec.from_html_vars("od") == "smth"
        with request_var(od="99"):
            assert valuespec.from_html_vars("od") == "id_a"

    def test_canonical_value(self) -> None:
        assert (
            vs.OptionalDropdownChoice[str](explicit=vs.TextInput(), choices=[]).canonical_value()
            == ""
        )


@pytest.mark.usefixtures("request_context")
def test_optional_dropdown_choice_shows_the_explicit_input_by_change_handler() -> None:
    valuespec = vs.OptionalDropdownChoice[str](
        explicit=vs.TextInput(), choices=[("id_a", "title_a")]
    )

    assert ts_function_call(render_input(valuespec, "id_a"), "select#vp") == (
        "valuespec_optional_dropdown_choice",
        {"div_id": "vp_ex"},
    )
