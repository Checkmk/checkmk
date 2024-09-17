#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

from cmk.gui.form_specs.private import ListOfStrings
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


class ListOfStringsVisitor(FormSpecVisitor[ListOfStrings, Sequence[str]]):
    def _parse_value(self, raw_value: object) -> Sequence[str] | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            return self.form_spec.prefill.value

        if not isinstance(raw_value, list):
            return EMPTY_VALUE

        for value in raw_value:
            if not isinstance(value, str):
                return EMPTY_VALUE

        # Filter empty strings
        return [x for x in raw_value if x]

    def _to_vue(
        self, raw_value: object, parsed_value: Sequence[str] | EmptyValue
    ) -> tuple[shared_type_defs.ListOfStrings, Sequence[str]]:
        if isinstance(parsed_value, EmptyValue):
            parsed_value = []

        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self.form_spec.string_spec, self.options)
        string_spec, string_default_value = element_visitor.to_vue(DEFAULT_VALUE)

        return (
            shared_type_defs.ListOfStrings(
                title=title,
                help=help_text,
                string_spec=string_spec,
                string_default_value=string_default_value,
            ),
            parsed_value or [""],
        )

    def _validate(
        self, raw_value: object, parsed_value: Sequence[str] | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(raw_value, Title("Invalid data for list"))

        element_validations = [
            *compute_validation_errors(compute_validators(self.form_spec), parsed_value)
        ]
        element_visitor = get_visitor(self.form_spec.string_spec, self.options)

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

    def _to_disk(self, raw_value: object, parsed_value: Sequence[str]) -> Sequence[str]:
        return parsed_value
