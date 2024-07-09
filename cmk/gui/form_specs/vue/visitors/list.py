#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import (
    FormSpecVisitor,
    InputHintValue,
    InvalidValue,
    ParsedValue,
    ValidateValue,
    ValidValue,
)
from cmk.gui.form_specs.vue.type_defs import DEFAULT_VALUE, default_value, Value, VisitorOptions
from cmk.gui.form_specs.vue.utils import (
    compute_parsed_value,
    compute_valid_value,
    compute_validation_errors,
    create_validation_error,
    get_title_and_help,
    get_visitor,
    migrate_value,
)
from cmk.gui.i18n import translate_to_current_language

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import List


class ListVisitor(FormSpecVisitor):
    def __init__(self, form_spec: List, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[list], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> ParsedValue[list]:
        value = migrate_value(self.form_spec, self.options, value)
        if isinstance(value, DEFAULT_VALUE):
            value = []
        return compute_parsed_value(value, False, list)

    def to_vue(self, parsed_value: ParsedValue[list]) -> tuple[VueComponents.List, Value]:
        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self.form_spec.element_template, self.options)
        element_default_value = element_visitor.parse_value(default_value)
        element_schema, element_vue_default_value = element_visitor.to_vue(element_default_value)

        value = compute_valid_value(parsed_value, [])
        list_values = []
        for entry in value:
            # Note: InputHints are not really supported for list elements
            #       We just collect data for a given template
            #       The data cannot be a mixture between values and InputHint
            element_parsed_value = element_visitor.parse_value(entry)
            _, element_vue_value = element_visitor.to_vue(element_parsed_value)
            list_values.append(element_vue_value)

        return (
            VueComponents.List(
                title=title,
                help=help_text,
                element_template=element_schema,
                element_default_value=element_vue_default_value,
                add_element_label=self.form_spec.add_element_label.localize(
                    translate_to_current_language
                ),
                remove_element_label=self.form_spec.remove_element_label.localize(
                    translate_to_current_language
                ),
                no_element_label=self.form_spec.no_element_label.localize(
                    translate_to_current_language
                ),
                editable_order=self.form_spec.editable_order,
            ),
            list_values,
        )

    def validate(self, parsed_value: ValidateValue[list]) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(parsed_value)

        element_validations = [*compute_validation_errors(self._validators(), parsed_value.value)]
        element_visitor = get_visitor(self.form_spec.element_template, self.options)

        for idx, entry in enumerate(parsed_value.value):
            element_parsed_value = element_visitor.parse_value(entry)
            if isinstance(element_parsed_value, InputHintValue):
                raise MKGeneralException(f"Cannot validate field {idx} with InputHint")
            for validation in element_visitor.validate(element_parsed_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[str(idx)] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )

        return element_validations

    def to_disk(self, parsed_value: ValidValue[list]) -> list:
        disk_values = []
        element_visitor = get_visitor(self.form_spec.element_template, self.options)

        for entry in parsed_value.value:
            element_parsed_value = element_visitor.parse_value(entry)
            if isinstance(element_parsed_value, (InputHintValue, InvalidValue)):
                raise MKGeneralException(
                    f"Cannot serialize entry of type {type(element_parsed_value)}"
                )
            disk_values.append(element_visitor.to_disk(element_parsed_value))

        return disk_values
