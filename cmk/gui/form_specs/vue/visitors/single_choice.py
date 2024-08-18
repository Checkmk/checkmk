#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generic, TypeVar

from cmk.gui.form_specs import private
from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import DefaultValue, EMPTY_VALUE, EmptyValue, Value
from cmk.gui.form_specs.vue.utils import (
    compute_text_input_hint,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
    migrate_value,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1 import Title

T = TypeVar("T")


class SingleChoiceVisitor(Generic[T], FormSpecVisitor[private.SingleChoiceExtended[T], T]):
    def _parse_value(self, raw_value: object) -> T | EmptyValue:
        raw_value = migrate_value(self.form_spec, self.options, raw_value)
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, self.form_spec.type):
            return EMPTY_VALUE
        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: T | EmptyValue
    ) -> tuple[VueComponents.SingleChoice, Value]:
        title, help_text = get_title_and_help(self.form_spec)

        elements = [
            VueComponents.SingleChoiceElementExtended(
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
                label=localize(self.form_spec.label),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                frozen=self.form_spec.frozen and isinstance(raw_value, str),
                input_hint=compute_text_input_hint(self.form_spec.prefill),
            ),
            "" if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: T | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(raw_value, Title("Invalid choice"))
        return compute_validation_errors(compute_validators(self.form_spec), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: T) -> T:
        return parsed_value
