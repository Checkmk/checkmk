#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import (
    expect_validate_failure,
    expect_validate_failure_untypeable,
    expect_validate_success,
    request_var,
)


def get_dropdown_choice(
    choices: vs.DropdownChoices = (("a", "ant"), ("b", "bee")),
    help_separator: str | None = None,
    invalid_choice: vs.DropdownInvalidChoice = "complain",
    invalid_choice_title: str | None = None,
    invalid_choice_error: str | None = None,
    no_preselect_title: str | None = None,
    read_only: bool = False,
    encode_value: bool = True,
    deprecated_choices: Sequence[object] = (),
    default_value: vs.ValueSpecDefault[str] = vs.DEF_VALUE,
) -> vs.DropdownChoice[str]:
    return vs.DropdownChoice[str](
        choices=choices,
        help_separator=help_separator,
        invalid_choice=invalid_choice,
        invalid_choice_title=invalid_choice_title,
        invalid_choice_error=invalid_choice_error,
        no_preselect_title=no_preselect_title,
        read_only=read_only,
        encode_value=encode_value,
        deprecated_choices=deprecated_choices,
        default_value=default_value,
    )


class TestValueSpecDropdownChoice:
    def test_validate(self) -> None:
        expect_validate_failure(
            get_dropdown_choice(),
            "asd",
            match="The selected element 'asd' is not longer available. Please select something else.",
        )
        expect_validate_failure(
            get_dropdown_choice(invalid_choice_error="smth"),
            "asd",
            match="smth",
        )
        expect_validate_success(
            get_dropdown_choice(invalid_choice="replace"),
            "asd",
        )
        expect_validate_failure_untypeable(
            get_dropdown_choice(),
            1,
            match="The value 1 has type int, but does not match any of the available choice types.",
        )
        expect_validate_failure(
            get_dropdown_choice(no_preselect_title="no preselect title"),
            None,
            match="Please make a selection",
        )
        with pytest.raises(
            MKUserError, match="There are no elements defined for this selection yet."
        ):
            # if validate_datatype is called before validate_value this can not happen!
            get_dropdown_choice(choices=[]).validate_value(None, "")

        # this one works, although its a typing error
        get_dropdown_choice(deprecated_choices=[77]).validate_datatype(77, "")  # type: ignore[arg-type]

    def test_mask(self) -> None:
        assert get_dropdown_choice().mask("hunter2") == "hunter2"

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(value="a"):
            assert get_dropdown_choice(encode_value=False).from_html_vars("value") == "a"

        with (
            request_var(value="smth"),
            pytest.raises(
                MKUserError,
                match="The selected element 'smth' is not longer available. Please select something else.",
            ),
        ):
            get_dropdown_choice(encode_value=False).from_html_vars("value")

        with request_var(value="d749929fe94b9a37dbe5d74cb297ad24b46e467898545f4e109eb21835046ac4"):
            assert get_dropdown_choice().from_html_vars("value") == "a"

        with (
            request_var(value="0000000000000000000000000000000000000000000000000000000000000000"),
            pytest.raises(
                MKUserError,
                match=(
                    "The selected element '0000000000000000000000000000000000000000000000000000000000000000' "
                    "is not longer available. Please select something else."
                ),
            ),
        ):
            assert get_dropdown_choice().from_html_vars("value") == "a"

        with (
            request_var(value="smth"),
            pytest.raises(
                MKUserError, match="There are no elements defined for this selection yet."
            ),
        ):
            get_dropdown_choice(choices=[]).from_html_vars("value")

        with request_var(value="smth"):
            _ = get_dropdown_choice(invalid_choice="replace").from_html_vars("value") == "a"

        with request_var(value="smth"):
            _ = (
                get_dropdown_choice(invalid_choice="replace", default_value="b").from_html_vars(
                    "value"
                )
                == "b"
            )

    def test_canonical_value(self) -> None:
        assert get_dropdown_choice().canonical_value() == "a"
        assert get_dropdown_choice(choices=[]).canonical_value() is None
        assert get_dropdown_choice(default_value="b", choices=[]).canonical_value() is None

    def test_default_value(self) -> None:
        assert get_dropdown_choice(default_value="b").default_value() == "b"
        # TODO: probably not a good idea, to have a default value, even if
        # there are no choices?
        assert get_dropdown_choice(default_value="b", choices=[]).default_value() == "b"

    def test_allow_empty(self) -> None:
        assert get_dropdown_choice(read_only=True, no_preselect_title="smth").allow_empty() is True
        assert get_dropdown_choice(read_only=True).allow_empty() is True

        assert get_dropdown_choice(no_preselect_title="smth").allow_empty() is False
        assert (
            get_dropdown_choice(read_only=False, no_preselect_title="smth").allow_empty() is False
        )

        assert get_dropdown_choice(read_only=False).allow_empty() is True
        # read_only defaults to False:
        assert get_dropdown_choice().allow_empty() is True

    def test_value_to_html(self) -> None:
        assert get_dropdown_choice(invalid_choice_title="INVALID!").value_to_html("z") == "INVALID!"
        assert get_dropdown_choice().value_to_html("b") == "bee"
        assert (
            get_dropdown_choice(
                help_separator=" - ", choices=[("a", "ant - ameise"), ("b", "bee - biene")]
            ).value_to_html("b")
            == "bee"
        )
