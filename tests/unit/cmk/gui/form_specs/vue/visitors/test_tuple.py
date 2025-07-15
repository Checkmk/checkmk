#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import Any

import pytest

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.vue import get_visitor, IncomingData, RawDiskData, RawFrontendData
from cmk.gui.form_specs.vue.visitors import (
    SingleChoiceVisitor,
)
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange, ValidationError


@pytest.fixture(scope="module", name="spec")
def tuple_spec() -> Tuple:
    return Tuple(
        title=Title("tuple title"),
        help_text=Help("tuple help"),
        elements=[
            Integer(
                title=Title(
                    "int title",
                ),
                custom_validate=(NumberInRange(min_value=1, max_value=12),),
                prefill=DefaultValue(7),
            ),
            String(title=Title("some string"), prefill=DefaultValue("default string")),
            Dictionary(
                title=Title("dict in tuple"),
                elements={
                    "test_float": DictElement(
                        required=True, parameter_form=Float(prefill=DefaultValue(42.0))
                    )
                },
            ),
            SingleChoice(
                title=Title("single choice in tuple"),
                elements=[
                    SingleChoiceElement(name="choice1", title=Title("Choice 1")),
                    SingleChoiceElement(name="choice2", title=Title("Choice 2")),
                ],
                prefill=DefaultValue("choice1"),
            ),
        ],
        layout="vertical",
        show_titles=True,
    )


@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        [
            RawFrontendData(
                [
                    7,
                    "default string",
                    {"test_float": 42.0},
                    SingleChoiceVisitor.option_id("choice1"),
                ]
            ),
            (7, "default string", {"test_float": 42.0}, "choice1"),
        ],
        [
            RawFrontendData(
                [
                    7,
                    "default string",
                    {"test_float": 42.0},
                    SingleChoiceVisitor.option_id("choice2"),
                ]
            ),
            (7, "default string", {"test_float": 42.0}, "choice2"),
        ],
    ],
)
def test_tuple_visitor_to_disk(spec: Tuple, value: IncomingData, expected_value: list[Any]) -> None:
    visitor = get_visitor(spec)
    disk_value = visitor.to_disk(value)
    assert disk_value == expected_value
    assert len(visitor.validate(value)) == 0


@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        [
            RawDiskData(
                (
                    7,
                    "default string",
                    {"test_float": 42.0},
                    "choice1",
                )
            ),
            [7, "default string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice1")],
        ],
        [
            RawDiskData(
                [
                    7,
                    "default string",
                    {"test_float": 42.0},
                    "choice2",
                ]
            ),
            [7, "default string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice2")],
        ],
    ],
)
def test_tuple_visitor_to_vue(spec: Tuple, value: IncomingData, expected_value: list[Any]) -> None:
    visitor = get_visitor(spec)
    assert visitor.to_vue(value)[1] == expected_value
    assert len(visitor.validate(value)) == 0


@pytest.mark.parametrize(
    ["invalid_value", "expected_errors"],
    [
        [RawDiskData((1, 2)), 1],  # wrong tuple length
        [RawDiskData(("asd", 2, {"test_float": 42.0}, "choice1")), 2],  # wrong data type
        [
            RawDiskData((15, "some_string", {"test_float": 42.0}, "choice2")),
            1,
        ],  # int validator failed
        [RawDiskData((1, "some_string", {}, "choice2")), 1],  # dict validator failed
        [
            RawDiskData((1, "some_string", {"test_float": 42.0}, "choice3")),
            1,
        ],  # single choice validator failed
    ],
)
def test_tuple_visitor_invalid_value(
    spec: Tuple,
    invalid_value: IncomingData,
    expected_errors: int,
) -> None:
    visitor = get_visitor(spec)
    assert len(visitor.validate(invalid_value)) == expected_errors


def test_tuple_validator() -> None:
    def _i_dont_like(unliked_value: object) -> Callable[[object], object]:
        def _validate(value: object) -> object:
            if value == unliked_value:
                raise ValidationError(Message("I don't like this value"))
            return value

        return _validate

    spec = Tuple(
        elements=[
            Integer(
                custom_validate=[_i_dont_like(5)],
            ),
        ],
        custom_validate=[_i_dont_like((1,))],
    )

    visitor = get_visitor(spec)

    assert len(visitor.validate(RawDiskData((0,)))) == 0
    assert len(visitor.validate(RawDiskData((1,)))) == 1
    assert len(visitor.validate(RawDiskData((5,)))) == 1
    assert len(visitor.validate(RawFrontendData([0]))) == 0
    assert len(visitor.validate(RawFrontendData([1]))) == 1
    assert len(visitor.validate(RawFrontendData([5]))) == 1
