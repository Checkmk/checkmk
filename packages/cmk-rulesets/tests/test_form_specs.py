#  !/usr/bin/env python3
#  Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    SingleChoice,
    SingleChoiceElement,
)


def test_fixed_value_validation_bool() -> None:
    FixedValue(value=True, title=Title(""))


def test_fixed_value_validation_int() -> None:
    FixedValue(value=0, title=Title(""))


def test_fixed_value_validation_float() -> None:
    FixedValue(value=42.0, title=Title(""))


def test_fixed_value_validation_str() -> None:
    FixedValue(value="juhu", title=Title(""))


def test_fixed_value_validation_fails() -> None:
    with pytest.raises(ValueError, match="FixedValue value is not serializable."):
        FixedValue(value=float("Inf"), title=Title("Test FixedValue"))


def test_dictionary_ident_validation() -> None:
    elements = {"element\abc": DictElement(parameter_form=FixedValue(value=None))}
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        Dictionary(elements=elements)


def test_multiple_choice_validation() -> None:
    with pytest.raises(ValueError, match="Invalid prefill element"):
        MultipleChoice(
            elements=[MultipleChoiceElement(name="element_abc", title=Title("Element ABC"))],
            prefill=DefaultValue(("element_xyz",)),
        )


def test_single_choice_validation() -> None:
    elements = (SingleChoiceElement(name="element_abc", title=Title("Element ABC")),)
    with pytest.raises(ValueError):
        SingleChoice(
            elements=elements,
            prefill=DefaultValue("element_xyz"),
        )


def test_cascading_single_choice_validation() -> None:
    elements = (
        CascadingSingleChoiceElement(
            name="element_abc",
            title=Title("Element ABC"),
            parameter_form=FixedValue(value=None),
        ),
    )
    with pytest.raises(ValueError):
        CascadingSingleChoice(
            elements=elements,
            prefill=DefaultValue("element_xyz"),
        )


def test_multiple_choice_element_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        MultipleChoiceElement(name="element\abc", title=Title("Element ABC"))


def test_single_choice_element_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        SingleChoiceElement(name="element\abc", title=Title("Element ABC"))


def test_cascading_single_choice_element_validation() -> None:
    with pytest.raises(ValueError, match="'element\x07bc' is not a valid Python identifier"):
        CascadingSingleChoiceElement(
            name="element\abc",
            title=Title("Element ABC"),
            parameter_form=FixedValue(value=None),
        )
