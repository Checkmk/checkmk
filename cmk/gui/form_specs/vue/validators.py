#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

import cmk.gui.form_specs.private.validators as private_form_specs_validators
from cmk.gui.form_specs.vue.type_defs import vue_validators
from cmk.gui.form_specs.vue.type_defs.vue_validators import VueValidators
from cmk.gui.i18n import _

import cmk.rulesets.v1.form_specs.validators as formspec_validators


def build_vue_validators(
    validators: Sequence[Callable[[Any], object]] | None,
) -> list[VueValidators]:
    if validators is None:
        return []
    result = []
    for validator in validators:
        result.extend(_build_vue_validator(validator))
    return result


def _build_vue_validator(validator: Callable[[Any], object]) -> list[VueValidators]:
    if isinstance(validator, formspec_validators.NumberInRange):
        min_validator = formspec_validators.NumberInRange(min_value=validator.range[0])
        max_validator = formspec_validators.NumberInRange(max_value=validator.range[1])
        return [
            # vue_validators.VueNumberInRange(
            #    min_value=validator.range[0],
            #    max_value=validator.range[1],
            #    error_message=validator.error_msg.localize(_),
            # ),
            vue_validators.NumberInRange(
                min_value=None,
                max_value=max_validator.range[1],
                error_message=max_validator.error_msg.localize(_),
            ),
            vue_validators.NumberInRange(
                min_value=min_validator.range[0],
                max_value=None,
                error_message=min_validator.error_msg.localize(_),
            ),
        ]
    if isinstance(validator, formspec_validators.LengthInRange):
        return [
            vue_validators.LengthInRange(
                min_value=validator.range[0],
                max_value=validator.range[1],
                error_message=validator.error_msg.localize(_),
            )
        ]
    if isinstance(validator, private_form_specs_validators.IsInteger):
        return [
            vue_validators.IsNumber(
                error_message=validator.error_msg.localize(_),
            )
        ]
    return []
