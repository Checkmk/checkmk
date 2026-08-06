#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable
from typing import override

import pytest

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.visitors import IncomingData
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


def _validate_integer_larger_than_10(value: object) -> None:
    if not isinstance(value, int) or value <= 10:
        raise validators.ValidationError(Message("Value must be an integer larger than 10"))


class _Unconvertible:
    @override
    def __str__(self):
        raise TypeError("Cannot convert to string")


def _build_value_validation_for_class_with_input_hint(
    class_type: type, prefill_value: object, good_values: list[object], bad_values: list[object]
) -> Iterable[tuple[FormSpec, object, bool]]:
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


pytestmark = pytest.mark.usefixtures("load_plugins")


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
                custom_validate=(_validate_integer_larger_than_10,),
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
    value: IncomingData,
    valid: bool,
) -> None:
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))

    assert (len(visitor.validate(value)) == 0) == valid
