#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Generic, TypeVar

from cmk.gui.form_specs import private
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import InvalidElementMode

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, EMPTY_VALUE, EmptyValue, Value
from ._utils import (
    compute_title_input_hint,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
)

T = TypeVar("T")


class SingleChoiceVisitor(Generic[T], FormSpecVisitor[private.SingleChoiceExtended[T], T]):
    def _is_valid_choice(self, value: T | EmptyValue) -> bool:
        if isinstance(value, EmptyValue):
            return False
        return value in [x.name for x in self.form_spec.elements]

    def _parse_value(self, raw_value: object) -> T | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, self.form_spec.type):
            return EMPTY_VALUE

        if not self._is_valid_choice(raw_value):
            # Note: An invalid choice does not always result in an empty value
            # invalid_element_validation: InvalidElementValidator:InvalidElementMode.KEEP
            #   Value is kept
            #       -> invalid element will be shown in the frontend, but can't be saved.
            #       -> invalid element will be written back _to_disk
            # invalid_element_validation: InvalidElementValidator:InvalidElementMode.COMPLAIN
            #   Value is considered invalid
            #       -> validate generates an error message
            #       -> to_vue generates an input hint, that the value is broken
            #       -> to_disk would fail
            # invalid_element_validation: None
            #   Same behaviour as COMPLAIN, but with generic error texts
            if (
                self.form_spec.invalid_element_validation
                and self.form_spec.invalid_element_validation.mode == InvalidElementMode.KEEP
            ):
                return raw_value
            return EMPTY_VALUE

        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: T | EmptyValue
    ) -> tuple[shared_type_defs.SingleChoice, Value]:
        title, help_text = get_title_and_help(self.form_spec)

        elements = [
            shared_type_defs.SingleChoiceElement(
                name=element.name,
                title=element.title.localize(translate_to_current_language),
            )
            for element in self.form_spec.elements
        ]

        input_hint = compute_title_input_hint(self.form_spec.prefill)
        if not self._is_valid_choice(parsed_value):
            parsed_value = EMPTY_VALUE
            invalid_validation = self.form_spec.invalid_element_validation
            if invalid_validation and invalid_validation.display:
                input_hint = localize(invalid_validation.display)

        return (
            shared_type_defs.SingleChoice(
                title=title,
                help=help_text,
                elements=elements,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                frozen=self.form_spec.frozen and isinstance(raw_value, self.form_spec.type),
                input_hint=input_hint,
            ),
            "" if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _compute_invalid_value_display_message(self, raw_value: object) -> str:
        # Note: The InvalidElementValidator class offers an error_message and a "display" message
        #       On error, the "display" message is shown as dropdown choice input hint
        message = (
            self.form_spec.invalid_element_validation
            and self.form_spec.invalid_element_validation.error_msg
        ) or Message("Invalid choice %r")
        message_localized = localize(message)
        if "%s" in message_localized or "%r" in message_localized:
            return message_localized % (raw_value,)
        return message_localized

    def _validate(
        self, raw_value: object, parsed_value: T | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue) or not self._is_valid_choice(parsed_value):
            return create_validation_error(
                "", self._compute_invalid_value_display_message(raw_value)
            )
        return compute_validation_errors(compute_validators(self.form_spec), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: T) -> T:
        return parsed_value
