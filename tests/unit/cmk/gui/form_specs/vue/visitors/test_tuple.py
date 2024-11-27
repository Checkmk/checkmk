#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    DEFAULT_VALUE,
    get_visitor,
    SingleChoiceVisitor,
    VisitorOptions,
)

from cmk.rulesets.v1 import Help, Title
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
from cmk.rulesets.v1.form_specs.validators import NumberInRange


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


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        [
            DEFAULT_VALUE,
            [7, "default string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice1")],
        ],
        [
            [9, DEFAULT_VALUE, DEFAULT_VALUE, "choice2"],
            [9, "default string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice2")],
        ],
        [
            [3, "some_string", DEFAULT_VALUE, DEFAULT_VALUE],
            [3, "some_string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice1")],
        ],
        [
            (3, "some_string", {"test_float": 42.0}, DEFAULT_VALUE),
            [3, "some_string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice1")],
        ],
    ],
)
def test_tuple_visitor_valid_value(
    spec: Tuple, data_origin: DataOrigin, value: list[Any] | tuple[Any], expected_value: list[Any]
) -> None:
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))
    vue_value = visitor.to_vue(value)[1]
    assert vue_value == expected_value
    assert len(visitor.validate(value)) == 0


@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        [
            [7, "default string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice1")],
            (7, "default string", {"test_float": 42.0}, "choice1"),
        ],
        [
            [7, "default string", {"test_float": 42.0}, SingleChoiceVisitor.option_id("choice2")],
            (7, "default string", {"test_float": 42.0}, "choice2"),
        ],
    ],
)
def test_tuple_visitor_to_disk(
    spec: Tuple, value: list[Any] | tuple[Any], expected_value: list[Any]
) -> None:
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    disk_value = visitor.to_disk(value)
    assert disk_value == expected_value
    assert len(visitor.validate(value)) == 0


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["invalid_value", "expected_errors"],
    [
        [(1, 2), 1],  # wrong tuple length
        [("asd", 2, {"test_float": 42.0}, "choice1"), 2],  # wrong data type
        [(15, "some_string", {"test_float": 42.0}, "choice2"), 1],  # int validator failed
        [(1, "some_string", {}, "choice2"), 1],  # dict validator failed
        [(1, "some_string", {"test_float": 42.0}, "choice3"), 1],  # single choice validator failed
    ],
)
def test_tuple_visitor_invalid_value(
    spec: Tuple,
    data_origin: DataOrigin,
    invalid_value: list[Any] | tuple[Any],
    expected_errors: int,
) -> None:
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))
    assert len(visitor.validate(invalid_value)) == expected_errors
