#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

import cmk.gui.form_specs.private.validators as private_form_specs_validators
import cmk.gui.form_specs.vue.autogen_type_defs.vue_formspec_components as VueComponents
from cmk.gui.i18n import _

import cmk.rulesets.v1.form_specs.validators as formspec_validators


def build_vue_validators(validators: Sequence[object]) -> list[VueComponents.Validators]:
    result = []
    for validator in validators:
        result.extend(_build_vue_validator(validator))
    return result


def _build_vue_validator(validator: object) -> list[VueComponents.Validators]:
    try:
        if build_function := _validator_registry.get(type(validator)):
            return build_function(validator)
    except AttributeError:
        pass
    return []


def _build_in_range_validator(
    validator: formspec_validators.NumberInRange,
) -> list[VueComponents.Validators]:
    value_from, value_to = validator.range
    assert not isinstance(value_from, float)
    assert not isinstance(value_to, float)
    min_validator = formspec_validators.NumberInRange(min_value=validator.range[0])
    max_validator = formspec_validators.NumberInRange(max_value=validator.range[1])
    return [
        VueComponents.NumberInRange(
            min_value=None,
            max_value=value_to,
            error_message=max_validator.error_msg.localize(_),
        ),
        VueComponents.NumberInRange(
            min_value=value_from,
            max_value=None,
            error_message=min_validator.error_msg.localize(_),
        ),
    ]


def _build_length_in_range_validator(
    validator: formspec_validators.LengthInRange,
) -> list[VueComponents.Validators]:
    value_from, value_to = validator.range
    assert not isinstance(value_from, float)
    assert not isinstance(value_to, float)
    return [
        VueComponents.LengthInRange(
            min_value=value_from,
            max_value=value_to,
            error_message=validator.error_msg.localize(_),
        )
    ]


def _build_is_integer_validator(
    validator: private_form_specs_validators.IsInteger,
) -> list[VueComponents.Validators]:
    return [
        VueComponents.IsInteger(
            error_message=validator.error_msg.localize(_),
        )
    ]


def _build_is_float_validator(
    validator: private_form_specs_validators.IsFloat,
) -> list[VueComponents.Validators]:
    return [
        VueComponents.IsFloat(
            error_message=validator.error_msg.localize(_),
        )
    ]


VueValidatorCreator = Callable[[Any], list[VueComponents.Validators]]
_validator_registry: dict[type, VueValidatorCreator] = {}


def register_class(validator_class: type, build_function: VueValidatorCreator) -> None:
    _validator_registry[validator_class] = build_function


def register_validators():
    register_class(formspec_validators.NumberInRange, _build_in_range_validator)
    register_class(formspec_validators.LengthInRange, _build_length_in_range_validator)
    register_class(private_form_specs_validators.IsInteger, _build_is_integer_validator)
    register_class(private_form_specs_validators.IsFloat, _build_is_float_validator)


register_validators()
