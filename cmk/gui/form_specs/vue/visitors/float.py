#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence

from cmk.gui.form_specs.private.validators import IsFloat
from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    EMPTY_VALUE,
    EmptyValue,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import (
    compute_input_hint,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
    migrate_value,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Float


class FloatVisitor(FormSpecVisitor):
    def __init__(self, form_spec: Float, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _parse_value(self, raw_value: object) -> float | EmptyValue:
        raw_value = migrate_value(self.form_spec, self.options, raw_value)
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default
        if not isinstance(raw_value, (float, int)):
            return EMPTY_VALUE
        return float(raw_value)

    def _validators(self) -> Sequence[Callable[[float], object]]:
        return [IsFloat()] + compute_validators(self.form_spec)

    def _to_vue(
        self, raw_value: object, parsed_value: float | EmptyValue
    ) -> tuple[VueComponents.Float, float | str]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            VueComponents.Float(
                title=title,
                help=help_text,
                unit=self.form_spec.unit_symbol,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=compute_input_hint(self.form_spec.prefill),
            ),
            "" if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: float | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if raw_value == DEFAULT_VALUE else raw_value, Title("Invalid float number")
            )
        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: float | EmptyValue) -> float:
        if isinstance(parsed_value, EmptyValue):
            raise MKGeneralException("Unable to serialize empty value")
        return parsed_value
