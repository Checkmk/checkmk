#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generic, Sequence, TypeVar

from cmk.gui.form_specs.private.list_extended import ListExtended
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1 import Title

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_title_and_help,
)

T = TypeVar("T")


class ListVisitor(Generic[T], FormSpecVisitor[ListExtended[T], Sequence[T]]):
    def _parse_value(self, raw_value: object) -> Sequence[T] | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            return self.form_spec.prefill.value

        if not isinstance(raw_value, list):
            return EMPTY_VALUE
        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: Sequence[T] | EmptyValue
    ) -> tuple[shared_type_defs.List, list[object]]:
        if isinstance(parsed_value, EmptyValue):
            # TODO: fallback to default message
            parsed_value = []

        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self.form_spec.element_template, self.options)
        element_schema, element_vue_default_value = element_visitor.to_vue(DEFAULT_VALUE)
        list_values = []
        for entry in parsed_value:
            # Note: InputHints are not really supported for list elements
            #       We just collect data for a given template
            #       The data cannot be a mixture between values and InputHint
            _, element_vue_value = element_visitor.to_vue(entry)
            list_values.append(element_vue_value)

        return (
            shared_type_defs.List(
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

    def _validate(
        self, raw_value: object, parsed_value: Sequence[T] | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(raw_value, Title("Invalid data for list"))

        element_validations = [
            *compute_validation_errors(compute_validators(self.form_spec), parsed_value)
        ]
        element_visitor = get_visitor(self.form_spec.element_template, self.options)

        for idx, entry in enumerate(parsed_value):
            for validation in element_visitor.validate(entry):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[str(idx)] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )
        return element_validations

    def _to_disk(self, raw_value: object, parsed_value: Sequence[T]) -> list[T]:
        disk_values = []
        element_visitor = get_visitor(self.form_spec.element_template, self.options)
        for entry in parsed_value:
            disk_values.append(element_visitor.to_disk(entry))
        return disk_values
