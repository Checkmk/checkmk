#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Mapping, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    EMPTY_VALUE,
    EmptyValue,
    Value,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import (
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
        return {key: DEFAULT_VALUE for key, el in self.form_spec.elements.items() if el.required}

    def _has_invalid_keys(self, value: dict) -> bool:
        valid_keys = self.form_spec.elements.keys()
        if len(set(value.keys() - valid_keys)) > 0:
            return True
        return False

    def _parse_value(self, raw_value: object) -> dict | EmptyValue:
        raw_value = migrate_value(self.form_spec, self.options, raw_value)
        raw_value = (
            self._compute_default_values() if isinstance(raw_value, DefaultValue) else raw_value
        )
        if not isinstance(raw_value, Mapping):
            return EMPTY_VALUE
        try:
            result_dict = dict(raw_value)
            if self._has_invalid_keys(result_dict):
                return EMPTY_VALUE
            return result_dict
        except ValueError:
            return EMPTY_VALUE

    def _to_vue(
        self, raw_value: object, parsed_value: dict | EmptyValue
    ) -> tuple[VueComponents.Dictionary, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, EmptyValue):
            # TODO: add warning message somewhere "falling back to defaults"
            parsed_value = self._compute_default_values()

        elements_keyspec = []
        vue_values = {}

        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in parsed_value
            element_value = parsed_value[key_name] if is_active else DEFAULT_VALUE
            element_schema, element_vue_value = element_visitor.to_vue(element_value)

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

    def _validate(
        self, raw_value: object, parsed_value: dict | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(raw_value, "Expected a valid value, got EmptyValue")

        # TODO: parse_result may include default values, e.g. {"ce": default_value}
        element_validations = [*self._validate_elements(parsed_value)]
        for key_name, dict_element in self.form_spec.elements.items():
            if key_name not in parsed_value:
                continue

            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            for validation in element_visitor.validate(parsed_value[key_name]):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[key_name] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )

        return element_validations

    def _to_disk(self, raw_value: object, parsed_value: dict | EmptyValue) -> dict:
        if isinstance(parsed_value, EmptyValue):
            raise MKGeneralException("Unable to serialize empty value")
        disk_values = {}
        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in parsed_value
            if is_active:
                disk_values[key_name] = element_visitor.to_disk(parsed_value[key_name])

        return disk_values
