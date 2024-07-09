#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Mapping, Sequence

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

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import Dictionary


class DictionaryVisitor(FormSpecVisitor):
    def __init__(self, form_spec: Dictionary, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[Mapping[str, object]], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def _compute_default_values(self) -> dict:
        return {key: default_value for key, el in self.form_spec.elements.items() if el.required}

    def _has_invalid_keys(self, parsed_value: ParsedValue[dict]) -> bool:
        valid_keys = self.form_spec.elements.keys()
        if isinstance(parsed_value, ValidValue):
            check_keys = set(parsed_value.value.keys())
            if len(check_keys - valid_keys) > 0:
                return True
        return False

    def parse_value(self, value: Any) -> ParsedValue[dict]:
        value = migrate_value(self.form_spec, self.options, value)
        value = self._compute_default_values() if isinstance(value, DEFAULT_VALUE) else value
        parsed_value = compute_parsed_value(value, False, dict)
        if isinstance(parsed_value, (InvalidValue, InputHintValue)):
            return parsed_value

        if self._has_invalid_keys(parsed_value):
            return InvalidValue(
                invalid_value=repr(parsed_value.value), error_message="Invalid keys in dictionary"
            )

        return parsed_value

    def to_vue(self, parsed_value: ParsedValue[dict]) -> tuple[VueComponents.Dictionary, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        value = compute_valid_value(parsed_value, self._compute_default_values())

        elements_keyspec = []
        vue_values = {}

        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in value
            element_parsed_value = element_visitor.parse_value(
                value[key_name] if is_active else default_value
            )

            element_schema, element_vue_value = element_visitor.to_vue(element_parsed_value)

            if is_active:
                vue_values[key_name] = element_vue_value

            elements_keyspec.append(
                VueComponents.DictionaryElement(
                    ident=key_name,
                    default_value=element_vue_value,
                    required=dict_element.required,
                    parameter_form=element_schema,
                )
            )

        return (
            VueComponents.Dictionary(title=title, help=help_text, elements=elements_keyspec),
            vue_values,
        )

    def _validate_elements(self, parsed_value: dict) -> list[VueComponents.ValidationMessage]:
        return compute_validation_errors(self._validators(), parsed_value)

    def validate(self, parsed_value: ValidateValue[dict]) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(parsed_value)

        element_validations = [*self._validate_elements(parsed_value.value)]
        for key_name, dict_element in self.form_spec.elements.items():
            if key_name not in parsed_value.value:
                continue

            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            element_parsed_value = element_visitor.parse_value(parsed_value.value[key_name])
            if isinstance(element_parsed_value, InputHintValue):
                raise MKGeneralException(f"Cannot validate field {key_name} with {InputHintValue}")
            for validation in element_visitor.validate(element_parsed_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[key_name] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )

        return element_validations

    def to_disk(self, parsed_value: ValidValue[dict]) -> dict:
        disk_values = {}
        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in parsed_value.value
            if is_active:
                element_parsed_value = element_visitor.parse_value(parsed_value.value[key_name])
                if isinstance(element_parsed_value, (InputHintValue, InvalidValue)):
                    raise MKGeneralException(
                        f"Cannot serialize field {key_name} with {type(element_parsed_value)}"
                    )
                disk_values[key_name] = element_visitor.to_disk(element_parsed_value)

        return disk_values
