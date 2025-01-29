#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private import OptionalChoice
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import DEFAULT_VALUE, VisitorOptions

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue, Integer


@pytest.fixture(scope="module", name="optional_choice_spec")
def spec() -> OptionalChoice:
    return OptionalChoice(
        title=Title("optional choice title"),
        help_text=Help("optional choice help"),
        label=Label("optional choice label"),
        none_label=Label("optional choice none label"),
        parameter_form=Integer(
            title=Title("Integer title"),
            prefill=DefaultValue(42),
        ),
    )


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["source_value", "expected_value"], [[42] * 2, [None] * 2, [DEFAULT_VALUE, None]]
)
def test_optional_choice_valid_value(
    optional_choice_spec: OptionalChoice,
    data_origin: DataOrigin,
    source_value: int | None | DefaultValue,
    expected_value: int | None,
) -> None:
    visitor = get_visitor(optional_choice_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(source_value)
    assert vue_value == expected_value

    # Check validation message
    validation_messages = visitor.validate(source_value)
    assert len(validation_messages) == 0

    # Same value returned to disk
    assert visitor.to_disk(source_value) == expected_value


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize("source_value", ["abc", (None,)])
def test_optional_choice_invalid_parameter_form_value(
    optional_choice_spec: OptionalChoice, data_origin: DataOrigin, source_value: str | tuple[None]
) -> None:
    class SomeClass:
        pass

    visitor = get_visitor(optional_choice_spec, VisitorOptions(data_origin=data_origin))
    _vue_spec, vue_value = visitor.to_vue(SomeClass)
    # Note: this is the INVALID_VALUE result of the embedded Integer parameter_form
    assert vue_value == ""

    # Check validation message
    validation_messages = visitor.validate(SomeClass)
    assert len(validation_messages) == 1

    # Invalid value causes exception
    with pytest.raises(MKGeneralException):
        visitor.to_disk(source_value)
