#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

from cmk.gui.form_specs.vue import shared_type_defs as VueComponents

VueValidatorCreator = Callable[[Any], list[VueComponents.Validator]]


def register_validator(validator_class: type, build_function: VueValidatorCreator) -> None:
    validator_registry[validator_class] = build_function


validator_registry: dict[type, VueValidatorCreator] = {}


def build_vue_validators(validators: Sequence[object]) -> list[VueComponents.Validator]:
    result = []
    for validator in validators:
        result.extend(_build_vue_validator(validator))
    return result


def _build_vue_validator(validator: object) -> list[VueComponents.Validator]:
    try:
        if build_function := validator_registry.get(type(validator)):
            return build_function(validator)
    except AttributeError:
        pass
    return []
