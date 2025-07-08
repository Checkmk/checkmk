#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Iterable
from typing import Any

import pytest

from cmk.gui.form_specs.vue import DEFAULT_VALUE, get_visitor, RawDiskData, RawFrontendData

from cmk.rulesets.v1 import Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    FixedValue,
    Float,
    FormSpec,
    InputHint,
    Integer,
    SIMagnitude,
    String,
    validators,
)


def _generate_validation_func(comparator: Callable[[Any], bool]) -> Callable[[Any], None]:
    def validation_func(value: Any) -> None:
        if not comparator(value):
            raise validators.ValidationError(Message("Validation failed"))

    return validation_func


class _Unconvertible:
    def __str__(self):
        raise TypeError("Cannot convert to string")


def _build_value_validation_for_class_with_input_hint(
    class_type: type, prefill_value: Any, good_values: list[Any], bad_values: list[Any]
) -> Iterable[tuple[FormSpec, Any, bool]]:
    for good_value in good_values:
        yield class_type(), good_value, True
        yield (
            class_type(
                prefill=DefaultValue(prefill_value),
            ),
            good_value,
            True,
        )

    for bad_value in bad_values:
        yield class_type(), bad_value, False
        yield (
            class_type(
                prefill=DefaultValue(prefill_value),
            ),
            bad_value,
            False,
        )

    yield class_type(), DEFAULT_VALUE, False
    yield class_type(prefill=DefaultValue(prefill_value)), DEFAULT_VALUE, True
    yield class_type(prefill=InputHint(prefill_value)), DEFAULT_VALUE, False


@pytest.mark.parametrize(
    "form_spec, value, valid",
    [
        (
            String(),
            RawDiskData("foo"),
            True,
        ),
        (
            String(
                custom_validate=(validators.LengthInRange(min_value=4),),
            ),
            RawDiskData("foo"),
            False,
        ),
        (
            String(
                custom_validate=(validators.LengthInRange(min_value=4),),
            ),
            RawDiskData("foobar"),
            True,
        ),
        (
            DataSize(
                displayed_magnitudes=[SIMagnitude.MEGA],
            ),
            RawDiskData(5),
            True,
        ),
        (
            DataSize(
                displayed_magnitudes=[SIMagnitude.MEGA],
                custom_validate=(
                    _generate_validation_func(
                        lambda x: x > 10,
                    ),
                ),
            ),
            RawDiskData(5),
            False,
        ),
        (
            CascadingSingleChoice(
                elements=[
                    CascadingSingleChoiceElement(
                        title=Title("None"),
                        name="none",
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="regex",
                        title=Title("Regex"),
                        parameter_form=String(),
                    ),
                ]
            ),
            RawFrontendData(
                [
                    "regex",
                    "some_string",
                ]
            ),
            True,
        ),
    ]
    + list(
        _build_value_validation_for_class_with_input_hint(
            Integer,
            5,
            [RawDiskData(5), RawDiskData(10), RawFrontendData(5), RawFrontendData(10)],
            [
                RawDiskData(10.1),
                RawDiskData("5"),
                RawDiskData("10"),
                RawDiskData("5.1"),
                RawDiskData("asdf"),
                RawDiskData({}),
                RawDiskData(None),
                RawFrontendData(10.1),
                RawFrontendData("10"),
                RawFrontendData("asdf"),
                RawFrontendData({}),
                RawFrontendData(None),
            ],
        )
    )
    + list(
        _build_value_validation_for_class_with_input_hint(
            Float,
            5.0,
            [
                RawDiskData(5.0),
                RawDiskData(10.0),
                RawDiskData(5),
                RawDiskData(10),
                RawFrontendData(5.0),
                RawFrontendData(10.0),
                RawFrontendData(5),
                RawFrontendData(10),
            ],
            [
                RawDiskData("5"),
                RawDiskData("10.0"),
                RawDiskData("asdf"),
                RawDiskData({}),
                RawDiskData(None),
                RawFrontendData("10"),
                RawFrontendData("10.1"),
                RawFrontendData("10.1.1"),
                RawFrontendData("asdf"),
                RawFrontendData({}),
                RawFrontendData(None),
            ],
        )
    )
    + list(
        _build_value_validation_for_class_with_input_hint(
            String,
            "5",
            [RawDiskData("10"), RawFrontendData("10")],
            [RawDiskData(_Unconvertible()), RawFrontendData(_Unconvertible())],
        )
    ),
)
def test_validation(
    form_spec: FormSpec,
    value: Any,
    valid: bool,
) -> None:
    visitor = get_visitor(form_spec)

    assert (len(visitor.validate(value)) == 0) == valid
