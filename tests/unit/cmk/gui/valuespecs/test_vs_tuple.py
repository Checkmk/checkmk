#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs

from .utils import expect_validate_failure, expect_validate_success, request_var


def get_tuple_vs() -> vs.Tuple[tuple[str, int, str, int]]:
    return vs.Tuple(
        elements=[
            vs.TextInput(),
            vs.Integer(),
            vs.Password(default_value="z"),
            vs.Integer(minvalue=1),
        ],
    )


class TestValueSpecTuple:
    def test_init(self) -> None:
        with pytest.raises(TypeError, match=" got an unexpected keyword argument 'default_value'"):
            # default_value was intentional removed
            vs.Tuple(
                elements=[
                    vs.TextInput(),
                    vs.Integer(),
                    vs.Password(default_value="z"),
                    vs.Integer(minvalue=1),
                ],
                default_value=None,
            )  # type: ignore[call-arg]

    def test_validate(self) -> None:
        expect_validate_success(get_tuple_vs(), ("", 0, "", 1))
        expect_validate_failure(get_tuple_vs(), ("", 0))  # type: ignore[misc]
        expect_validate_failure(get_tuple_vs(), ())  # type: ignore[misc]
        expect_validate_failure(get_tuple_vs(), (0, "", 0, ""))  # type: ignore[misc]
        expect_validate_failure(get_tuple_vs(), ["", 0, "", 1])  # type: ignore[misc]

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(v_0="a", v_1="2", v_2="c", v_3="4"):
            assert get_tuple_vs().from_html_vars("v") == ("a", 2, "c", 4)

    def test_value_to_html(self) -> None:
        assert get_tuple_vs().value_to_html(("a", 2, "c", 4)) == "a, 2, ******, 4"

    def test_mask(self) -> None:
        assert get_tuple_vs().mask(("a", 2, "c", 4)) == ("a", 2, "******", 4)

    def test_default_value(self) -> None:
        assert get_tuple_vs().default_value() == ("", 0, "z", 1)

    def test_json(self) -> None:
        assert get_tuple_vs().value_from_json(["a", 2, "c", 4]) == (
            "a",
            2,
            "c",
            4,
        )
        assert get_tuple_vs().value_to_json(("a", 2, "c", 4)) == [
            "a",
            2,
            "c",
            4,
        ]
