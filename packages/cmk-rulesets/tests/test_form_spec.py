#  !/usr/bin/env python3
#  Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DictElement,
    Dictionary,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    SingleChoice,
    SingleChoiceElement,
)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(True, id="bool"),
        pytest.param(0, id="int"),
        pytest.param(2.0, id="float"),
        pytest.param("value", id="float"),
        pytest.param(None, id="None"),
    ],
)
def test_fixed_value_validation(
    value: int | float | str | bool | None,
) -> None:
    FixedValue(value=value, title=Localizable("Test FixedValue"))


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(float("Inf"), id="Inf float"),
    ],
)
def test_fixed_value_validation_fails(value: int | float | str | bool | None) -> None:
    with pytest.raises(ValueError, match="FixedValue value is not serializable."):
        FixedValue(value=value, title=Localizable("Test FixedValue"))


def test_dictionary_ident_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        Dictionary(elements={"element\abc": DictElement(FixedValue(None))})


def test_multiple_choice_validation() -> None:
    with pytest.raises(ValueError, match="Default element is not one of the specified elements"):
        MultipleChoice(
            elements=[MultipleChoiceElement(name="element_abc", title=Localizable("Element ABC"))],
            prefill_selections=["element_xyz"],
        )


def test_single_choice_validation() -> None:
    with pytest.raises(ValueError, match="Default element is not one of the specified elements"):
        SingleChoice(
            elements=[SingleChoiceElement(name="element_abc", title=Localizable("Element ABC"))],
            prefill_selection="element_xyz",
        )


def test_cascading_single_choice_validation() -> None:
    with pytest.raises(ValueError, match="Default element is not one of the specified elements"):
        CascadingSingleChoice(
            elements=[
                CascadingSingleChoiceElement(
                    name="element_abc",
                    title=Localizable("Element ABC"),
                    parameter_form=FixedValue(None),
                )
            ],
            prefill_selection="element_xyz",
        )


def test_multiple_choice_element_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        MultipleChoiceElement(name="element\abc", title=Localizable("Element ABC"))


def test_single_choice_element_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        SingleChoiceElement(name="element\abc", title=Localizable("Element ABC"))


def test_cascading_single_choice_element_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        CascadingSingleChoiceElement(
            name="element\abc",
            title=Localizable("Element ABC"),
            parameter_form=FixedValue(None),
        )
