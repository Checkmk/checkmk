#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import expect_validate_failure, expect_validate_success, request_var


def get_cascading_dropdown(**arguments: Any) -> vs.CascadingDropdown:
    return vs.CascadingDropdown(
        choices=[
            ("long", "long title", vs.TextInput()),
            ("none1", "none1 title", None),
            ("none2", "none2 title"),
            (20, "integer ident title", vs.Password()),
            (None, "none ident title"),
            (False, "bool ident title"),
        ],
        **arguments,
    )


class TestCascadingDropDown:
    def test_default_value(self) -> None:
        assert get_cascading_dropdown().default_value() == ("long", "")
        assert vs.CascadingDropdown([]).default_value() is None
        assert vs.CascadingDropdown([("none1", "none1 title", None)]).default_value() == "none1"
        assert get_cascading_dropdown(default_value=(20, "smth")).default_value() == (20, "smth")

    def test_canonical_value(self) -> None:
        assert get_cascading_dropdown().canonical_value() == ("long", "")
        assert vs.CascadingDropdown([]).canonical_value() is None
        assert vs.CascadingDropdown([("none1", "none1 title", None)]).canonical_value() == "none1"

    def test_mask(self) -> None:
        assert get_cascading_dropdown().mask((20, "pwd")) == (20, "******")
        assert get_cascading_dropdown().mask("none2") == "none2"
        with pytest.raises(ValueError, match=r"Could not find an entry matching True in choices"):
            get_cascading_dropdown().mask((True, "pwd"))
        # although we pass an invalid value (would expect an string instead of
        # int (2222)) to cascading dropdown, it's simply passed to the embedded
        # valuespec. this was not the case in the previous implementation.
        assert get_cascading_dropdown().mask((20, 2222)) == (20, "******")

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(c_sel="0", c_0="smth"):
            assert get_cascading_dropdown().from_html_vars("c") == ("long", "smth")
        with request_var(c_sel="1"):
            assert get_cascading_dropdown().from_html_vars("c") == "none1"
        with request_var():
            assert vs.CascadingDropdown([]).from_html_vars("c") is None

    def test_validate(self) -> None:
        expect_validate_success(get_cascading_dropdown(), "none2")
        expect_validate_failure(  # type: ignore[misc]
            get_cascading_dropdown(),
            ("long", "2", None),
            match="If value is a tuple it has to have length of two.",
        )
        expect_validate_failure(  # type: ignore[misc]
            get_cascading_dropdown(),
            ("none1", "2", None),
            match="If value is a tuple it has to have length of two.",
        )
        expect_validate_success(get_cascading_dropdown(), None)
        expect_validate_failure(
            get_cascading_dropdown(no_preselect_title="no preselect title"), None
        )
        expect_validate_failure(
            get_cascading_dropdown(),
            "none9",
            match="Could not find an entry matching 'none9' in choices",
        )
        expect_validate_failure(
            get_cascading_dropdown(),
            ("none9", "smth"),
            match=r"Could not find an entry matching 'none9' in choices",
        )
        with pytest.raises(MKUserError, match=r"Value \('none9', 'smth'\) is not allowed here."):
            get_cascading_dropdown().validate_value(("none9", "smth"), "c")

        # Basic test for validate function of CascadingDropdown
        valuespec = vs.CascadingDropdown(
            choices=[
                (
                    "direct",
                    "Direct URL",
                    vs.TextInput(),
                ),
            ],
        )
        expect_validate_success(valuespec, ("direct", "smth"))
        expect_validate_failure(
            valuespec,
            ("zzzzzz", "smth"),
            match=r"Could not find an entry matching 'zzzzzz' in choices",
        )

    def test_value_to_json(self) -> None:
        with pytest.raises(ValueError, match="Could not find an entry matching 'some' in choices"):
            vs.CascadingDropdown([]).value_to_json(("some", "ignored value"))

        assert get_cascading_dropdown().value_to_json("none1") == "none1"
        assert get_cascading_dropdown().value_to_json(("long", "smth")) == ["long", "smth"]
        # in a previous implementation this would return None, as it was
        # calling validate_datatype to make sure the choice exists. as there
        # are many examples of Valuepsecs that do not validate the data in
        # value_to_json (Integer does not check min/max, ListOfStrings does not
        # check max_entries or allow_empty) we do not validate, but pass the
        # "illegal" value.
        assert get_cascading_dropdown().value_to_json(("long", 2222)) == ["long", 2222]

    def test_value_from_json(self) -> None:
        assert vs.CascadingDropdown([]).value_from_json(("some", "ignored value")) == (
            "some",
            "ignored value",
        )
        assert get_cascading_dropdown().value_from_json("none1") == "none1"
        assert get_cascading_dropdown().value_from_json(["long", "smth"]) == ("long", "smth")
        # see long comment on (long, 2222) test case in test_value_to_json
        assert get_cascading_dropdown().value_from_json(["long", 2222]) == ("long", 2222)
