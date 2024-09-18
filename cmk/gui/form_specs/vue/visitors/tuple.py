#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.vue import shared_type_defs

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


class TupleVisitor(FormSpecVisitor[Tuple, tuple[object, ...]]):
    def _parse_value(self, raw_value: object) -> tuple[Any, ...] | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            return (DEFAULT_VALUE,) * len(self.form_spec.elements)

        if not isinstance(raw_value, (list, tuple)):
            return EMPTY_VALUE

        if len(raw_value) != len(self.form_spec.elements):
            return EMPTY_VALUE

        return tuple(raw_value)

    def _to_vue(
        self, raw_value: object, parsed_value: tuple[Any, ...] | EmptyValue
    ) -> tuple[shared_type_defs.Tuple, list[object]]:
        title, help_text = get_title_and_help(self.form_spec)
        vue_specs = []
        vue_elements = []

        if isinstance(parsed_value, EmptyValue):
            parsed_value = (DEFAULT_VALUE,) * len(self.form_spec.elements)

        for element_spec, value in zip(self.form_spec.elements, parsed_value):
            element_vue, element_value = get_visitor(element_spec, self.options).to_vue(value)
            vue_specs.append(element_vue)
            vue_elements.append(element_value)

        return (
            shared_type_defs.Tuple(
                title=title,
                help=help_text,
                elements=vue_specs,
                layout=shared_type_defs.TupleLayout(self.form_spec.layout),
                show_titles=self.form_spec.show_titles,
            ),
            vue_elements,
        )

    def _validate(
        self, raw_value: object, parsed_value: tuple[object, ...] | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if isinstance(raw_value, DefaultValue) else raw_value,
                Title("Invalid tuple"),
            )

        validation_errors = compute_validation_errors(
            compute_validators(self.form_spec), parsed_value
        )
        for idx, (element_spec, value) in enumerate(zip(self.form_spec.elements, parsed_value)):
            element_visitor = get_visitor(element_spec, self.options)
            for validation in element_visitor.validate(value):
                validation_errors.append(
                    shared_type_defs.ValidationMessage(
                        location=[str(idx)] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )
        return validation_errors

    def _to_disk(self, raw_value: object, parsed_value: tuple[object, ...]) -> tuple[object, ...]:
        return parsed_value
