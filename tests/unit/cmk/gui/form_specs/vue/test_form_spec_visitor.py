#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Iterable
from typing import Any

import pytest

from cmk.ccc.user import UserId

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin, DEFAULT_VALUE
from cmk.gui.session import UserContext

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
            "foo",
            True,
        ),
        (
            String(
                custom_validate=(validators.LengthInRange(min_value=4),),
            ),
            "foo",
            False,
        ),
        (
            String(
                custom_validate=(validators.LengthInRange(min_value=4),),
            ),
            "foobar",
            True,
        ),
        (
            DataSize(
                displayed_magnitudes=[SIMagnitude.MEGA],
            ),
            5,
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
            5,
            False,
        ),
    ]
    + list(
        _build_value_validation_for_class_with_input_hint(
            Integer, 5, [5, 10, 5, 10], [10.1, "5", "10", "5.1", "asdf", {}, None]
        )
    )
    + list(
        _build_value_validation_for_class_with_input_hint(
            Float, 5.0, [5.0, 10.0, 5, 10], ["5", "10.0", "asdf", {}, None]
        )
    )
    + list(
        _build_value_validation_for_class_with_input_hint(String, "5", ["10"], [_Unconvertible()])
    ),
)
def test_validation(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    form_spec: FormSpec,
    value: Any,
    valid: bool,
) -> None:
    with UserContext(with_user[0]):
        vue_app_config = serialize_data_for_frontend(
            form_spec,
            "foo_field_id",
            DataOrigin.DISK,
            do_validate=True,
            value=value,
        )

        assert (not vue_app_config.validation) == valid


@pytest.mark.parametrize(
    "form_spec, value, valid",
    [
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
            [
                "regex",
                "some_string",
            ],
            True,
        )
    ]
    + list(
        _build_value_validation_for_class_with_input_hint(
            Integer, 5, [5, 10], [10.1, "10", "asdf", {}, None]
        )
    )
    + list(
        _build_value_validation_for_class_with_input_hint(
            Float, 5.0, [5.0, 10.0, 5, 10], ["10", "10.1", "10.1.1", "asdf", {}, None]
        )
    )
    + list(
        _build_value_validation_for_class_with_input_hint(String, "5", ["10"], [_Unconvertible()])
    ),
)
def test_validation_frontend(
    request_context: None,
    patch_theme: None,
    with_user: tuple[UserId, str],
    form_spec: FormSpec,
    value: Any,
    valid: bool,
) -> None:
    with UserContext(with_user[0]):
        vue_app_config = serialize_data_for_frontend(
            form_spec,
            "foo_field_id",
            DataOrigin.FRONTEND,
            do_validate=True,
            value=value,
        )

        assert (not vue_app_config.validation) == valid
