#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.html import HTML

from .utils import expect_validate_failure, expect_validate_success, raise_exception, request_var

FAILURE_MATCH = "The data type of the value does not match any of the allowed alternatives."


def get_alternative(**arguments: Any) -> vs.Alternative:
    return vs.Alternative(
        [
            vs.Integer(default_value=1),
            vs.TextInput(title="text"),
            vs.Tuple(elements=[vs.Integer(), vs.Integer()]),
            vs.Tuple(elements=[vs.Integer(), vs.Integer(), vs.Integer()]),
        ],
        **arguments,
    )


class TestValuespecAlternative:
    def _validate(self, arguments: dict[str, Any]) -> None:
        expect_validate_success(get_alternative(**arguments), 1)
        expect_validate_success(get_alternative(**arguments), "eins")
        expect_validate_success(get_alternative(**arguments), (2, 3))
        expect_validate_success(get_alternative(**arguments), (2, 3, 4))
        expect_validate_failure(get_alternative(**arguments), ("eins", "zwei"), match=FAILURE_MATCH)
        expect_validate_failure(get_alternative(**arguments), tuple(), match=FAILURE_MATCH)
        expect_validate_failure(get_alternative(**arguments), {}, match=FAILURE_MATCH)

        with pytest.raises(MKUserError, match=FAILURE_MATCH):
            # expect_validate_failure executes validate_datatype first,
            # but we want to also cover this code path!
            get_alternative(**arguments).validate_value(object, "")

    def test_validate(self) -> None:
        self._validate({})

    def test_validate_match(self) -> None:
        def _match(value: int | str | tuple) -> int:
            # creative way to match the value to the index of alternatives
            if isinstance(value, int):
                return 0
            if isinstance(value, str):
                return 1
            if isinstance(value, tuple):
                return len(value)
            raise MKUserError("", message=FAILURE_MATCH)

        self._validate({"match": _match})

    def test_canonical_value(self) -> None:
        assert get_alternative().canonical_value() == 0
        assert vs.Alternative([vs.TextInput()]).canonical_value() == ""

    def test_default_value(self) -> None:
        assert get_alternative().default_value() == 1
        assert get_alternative(default_value="zwei").default_value() == "zwei"
        assert get_alternative(default_value=lambda: "drei").default_value() == "drei"
        assert get_alternative(default_value=raise_exception).default_value() == 1

    def test_mask(self) -> None:
        assert get_alternative().mask(1) == 1
        assert get_alternative().mask("eins") == "eins"
        with pytest.raises(ValueError, match=r"^Invalid value: \('zwei', 'drei'\)"):
            get_alternative().mask(("zwei", "drei"))

    def test_value_to_html(self) -> None:
        assert get_alternative().value_to_html("testing") == "testing"
        assert get_alternative().value_to_html({}) == "invalid: {}"
        assert get_alternative(show_alternative_title=True).value_to_html(
            "testing"
        ) == HTML.without_escaping("text<br />testing")

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(a_use="2", a_2_0="2", a_2_1="3"):
            assert get_alternative().from_html_vars("a") == (2, 3)

    def test_value_to_json(self) -> None:
        assert get_alternative().value_to_json((2, 3)) == [2, 3]
        assert get_alternative().value_to_json("eins") == "eins"
        with pytest.raises(ValueError, match=r"^Invalid value: \('a', 'b'\)"):
            assert get_alternative().value_to_json(("a", "b"))

    def test_value_from_json(self) -> None:
        # TODO: this is wrong! should be transformed into a tuple,
        # see comment on Value_from_json
        assert get_alternative().value_from_json([2, 3]) == [2, 3]
