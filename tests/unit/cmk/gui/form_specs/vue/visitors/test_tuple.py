#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.vue.visitors import DataOrigin, DEFAULT_VALUE, get_visitor, VisitorOptions

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, Float, Integer, String
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
        ],
        layout="vertical",
        show_titles=True,
    )


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["value", "expected_value"],
    [
        [DEFAULT_VALUE, [7, "default string", {"test_float": 42.0}]],
        [[9, DEFAULT_VALUE, DEFAULT_VALUE], [9, "default string", {"test_float": 42.0}]],
        [[3, "some_string", {}], [3, "some_string", {}]],
        [(3, "some_string", {}), [3, "some_string", {}]],
    ],
)
def test_tuple_visitor_valid_value(
    spec: Tuple, data_origin: DataOrigin, value: list[Any] | tuple[Any], expected_value: list[Any]
) -> None:
    visitor = get_visitor(spec, VisitorOptions(data_origin=DataOrigin.DISK))
    vue_value = visitor.to_vue(value)[1]
    assert vue_value == expected_value
    assert len(visitor.validate(value)) == 0


@pytest.mark.parametrize("data_origin", [DataOrigin.DISK, DataOrigin.FRONTEND])
@pytest.mark.parametrize(
    ["invalid_value", "expected_errors"],
    [
        [(1, 2), 1],  # wrong tuple length
        [("asd", 2, {}), 2],  # wrong data type
        [(15, "some_string", {}), 1],  # int validator failed
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
