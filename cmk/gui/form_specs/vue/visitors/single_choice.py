#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Generic, TypeGuard, TypeVar

from cmk.gui.form_specs import private
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _, translate_to_current_language

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import InvalidElementMode
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, InvalidValue
from ._utils import (
    base_i18n_form_spec,
    compute_title_input_hint,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
    option_id,
)

T = TypeVar("T")

NO_SELECTION = None

_ParsedValueModel = object
_FrontendModel = str | None


class SingleChoiceVisitor(
    Generic[T], FormSpecVisitor[private.SingleChoiceExtended[T], _ParsedValueModel, _FrontendModel]
):
    def _is_valid_choice(self, value: object) -> TypeGuard[T]:
        if isinstance(value, InvalidValue):
            return False
        if not self.form_spec.elements:
            return False
        return value in [x.name for x in self.form_spec.elements]

    @classmethod
    def option_id(cls, val: object) -> str:
        return option_id(val)

    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if isinstance(raw_value, DefaultValue):
            fallback_value: _FrontendModel = NO_SELECTION
            if isinstance(
                prefill_default := get_prefill_default(
                    self.form_spec.prefill, fallback_value=fallback_value
                ),
                InvalidValue,
            ):
                return InvalidValue(
                    reason=self._compute_invalid_value_display_message(raw_value),
                    fallback_value=NO_SELECTION,
                )
            raw_value = prefill_default

        if self.options.data_origin == DataOrigin.FRONTEND:
            # Decode option send from frontend
            for option in self.form_spec.elements:
                if self.option_id(option.name) == raw_value:
                    raw_value = option.name
                    break
            else:
                # Found no matching option
                return InvalidValue(
                    reason=self._compute_invalid_value_display_message(raw_value),
                    fallback_value=NO_SELECTION,
                )

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
                # This is the only case where we might return `object` instead of T
                return raw_value
            return InvalidValue(
                reason=self._compute_invalid_value_display_message(raw_value),
                fallback_value=NO_SELECTION,
            )

        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.SingleChoice, str | None]:
        title, help_text = get_title_and_help(self.form_spec)

        elements = [
            shared_type_defs.SingleChoiceElement(
                name=self.option_id(element.name),
                title=element.title.localize(translate_to_current_language),
            )
            for element in self.form_spec.elements
        ]

        input_hint = compute_title_input_hint(self.form_spec.prefill)
        if not self._is_valid_choice(parsed_value):
            parsed_value = InvalidValue(
                reason=self._compute_invalid_value_display_message(raw_value),
                fallback_value=NO_SELECTION,
            )
            invalid_validation = self.form_spec.invalid_element_validation
            if invalid_validation and invalid_validation.display:
                input_hint = localize(invalid_validation.display)

        # Note: All valid values have at least some kind of str content,
        #       since self._option_id uses repr() to generate the id
        return (
            shared_type_defs.SingleChoice(
                title=title,
                help=help_text,
                elements=elements,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                frozen=self.form_spec.frozen and self._is_valid_choice(raw_value),
                input_hint=input_hint or _("Please choose"),
                no_elements_text=localize(self.form_spec.no_elements_text),
                i18n_base=base_i18n_form_spec(),
            ),
            parsed_value.fallback_value
            if isinstance(parsed_value, InvalidValue)
            else self.option_id(parsed_value),
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
            if raw_value == NO_SELECTION:
                return message_localized.replace("%s", "").replace("%r", "")
            return message_localized % (raw_value,)
        return message_localized

    def _validate(
        self, raw_value: object, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        if not self._is_valid_choice(parsed_value):
            return create_validation_error(
                NO_SELECTION, self._compute_invalid_value_display_message(raw_value)
            )
        return []

    def _to_disk(self, raw_value: object, parsed_value: _ParsedValueModel) -> object:
        return parsed_value
