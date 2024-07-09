#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

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
    compute_valid_value,
    compute_validation_errors,
    create_validation_error,
    get_title_and_help,
    migrate_value,
    process_prefills_with_title,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1.form_specs import SingleChoice


class SingleChoiceVisitor(FormSpecVisitor):
    def __init__(self, form_spec: SingleChoice, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[str], object]]:
        # TODO: add special __post_init__ / ignored_elements / invalid element
        #      validators for this form spec
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> ParsedValue[str]:
        value = migrate_value(self.form_spec, self.options, value)
        value, is_input_hint = process_prefills_with_title(self.form_spec, value)
        return compute_parsed_value(value, is_input_hint, str)

    def to_vue(self, parsed_value: ParsedValue[str]) -> tuple[VueComponents.SingleChoice, Value]:
        title, help_text = get_title_and_help(self.form_spec)

        elements = [
            VueComponents.SingleChoiceElement(
                name=element.name,
                title=element.title.localize(translate_to_current_language),
            )
            for element in self.form_spec.elements
        ]
        return (
            VueComponents.SingleChoice(
                title=title,
                help=help_text,
                elements=elements,
                validators=build_vue_validators(self._validators()),
                frozen=self.form_spec.frozen,
                input_hint=compute_input_hint(self.form_spec),
            ),
            compute_valid_value(parsed_value, ""),
        )

    def validate(self, parsed_value: ValidateValue[str]) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(parsed_value)
        return compute_validation_errors(self._validators(), parsed_value.value)

    def to_disk(self, parsed_value: ValidValue[str]) -> str:
        return parsed_value.value
