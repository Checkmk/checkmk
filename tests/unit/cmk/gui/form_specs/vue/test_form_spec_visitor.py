#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable

import pytest

from cmk.utils.user import UserId

from cmk.gui.form_specs.vue.form_spec_visitor import serialize_data_for_frontend
from cmk.gui.form_specs.vue.type_defs import DataOrigin
from cmk.gui.session import UserContext

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FormSpec,
    SIMagnitude,
    String,
    validators,
)


def test_dictionary_visitor_only_fills_required_prefill():
    form_spec = Dictionary(
        elements={
            "required_el": DictElement(
                parameter_form=String(
                    prefill=DefaultValue("el1_prefill"),
                ),
                required=True,
            ),
            "optional_el": DictElement(
                parameter_form=String(
                    prefill=DefaultValue("el2_prefill"),
                ),
            ),
        },
    )

    vue_app_config = serialize_data_for_frontend(
        form_spec, "foo_field_id", DataOrigin.DISK, do_validate=False
    )

    assert vue_app_config.data == {
        "required_el": "el1_prefill",
    }


def _generate_validation_func(comparator: Callable[[Any], bool]) -> Callable[[Any], None]:
    def validation_func(value: Any) -> None:
        if not comparator(value):
            raise validators.ValidationError(Message("Validation failed"))

    return validation_func


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
    ],
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
