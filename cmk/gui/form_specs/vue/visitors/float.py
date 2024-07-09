#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

from cmk.gui.form_specs.private.validators import IsFloat
from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import (
    FormSpecVisitor,
    InvalidValue,
    ParsedValue,
    ValidateValue,
    ValidValue,
)
from cmk.gui.form_specs.vue.type_defs import Value, VisitorOptions
from cmk.gui.form_specs.vue.utils import (
    compute_input_hint,
    compute_parsed_value,
    compute_text_input_value,
    compute_validation_errors,
    create_validation_error,
    get_title_and_help,
    localize,
    migrate_value,
    process_prefills,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1.form_specs import Float


class FloatVisitor(FormSpecVisitor):
    def __init__(self, form_spec: Float, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def parse_value(self, value: Any) -> ParsedValue[float]:
        value = migrate_value(self.form_spec, self.options, value)
        value, is_input_hint = process_prefills(self.form_spec, value)
        return compute_parsed_value(value, is_input_hint, float)

    def _validators(self) -> Sequence[Callable[[float], object]]:
        return [IsFloat()] + (
            list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []
        )

    def to_vue(self, parsed_value: ParsedValue[float]) -> tuple[VueComponents.Float, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            VueComponents.Float(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=compute_input_hint(self.form_spec),
            ),
            compute_text_input_value(parsed_value),
        )

    def validate(self, parsed_value: ValidateValue[float]) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(parsed_value)
        return compute_validation_errors(self._validators(), parsed_value.value)

    def to_disk(self, parsed_value: ValidValue[float]) -> float:
        return parsed_value.value
