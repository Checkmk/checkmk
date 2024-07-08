#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DataOrigin,
    DEFAULT_VALUE,
    default_value,
    Value,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import compute_validation_errors, get_title_and_help, get_visitor
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1.form_specs import List


class ListVisitor(FormSpecVisitor):
    def __init__(self, form_spec: List, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[list], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> list:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = []

        if not isinstance(value, list):
            raise TypeError(f"Expected a list, got {type(value)}")

        return value

    def to_vue(self, value: list) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self.form_spec.element_template, self.options)
        element_default_value = element_visitor.parse_value(default_value)
        element_schema, element_vue_default_value = element_visitor.to_vue(element_default_value)

        vue_values = []
        for element_value in value:
            parsed_element_value = element_visitor.parse_value(element_value)
            _, element_vue_value = element_visitor.to_vue(parsed_element_value)
            vue_values.append(element_vue_value)

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
            vue_values,
        )

    def _validate_elements(self, value: list) -> list[VueComponents.ValidationMessage]:
        return compute_validation_errors(self._validators(), value)

    def validate(self, value: list) -> list[VueComponents.ValidationMessage]:
        element_validations = [*self._validate_elements(value)]
        element_visitor = get_visitor(self.form_spec.element_template, self.options)

        for idx, element_value in enumerate(value):
            parsed_element_value = element_visitor.parse_value(element_value)
            element_value = element_visitor.parse_value(parsed_element_value)
            for validation in element_visitor.validate(element_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[str(idx)] + validation.location, message=validation.message
                    )
                )

        return element_validations

    def to_disk(self, value: list) -> Any:
        disk_values = []
        element_visitor = get_visitor(self.form_spec.element_template, self.options)

        for element_value in value:
            parsed_element_value = element_visitor.parse_value(element_value)
            element_value = element_visitor.parse_value(parsed_element_value)
            disk_values.append(element_visitor.to_disk(element_value))

        return disk_values
