#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeGuard, TypeVar

from cmk.gui.form_specs import private
from cmk.gui.form_specs.vue._base import FormSpecVisitor
from cmk.gui.form_specs.vue._utils import (
    base_i18n_form_spec,
    compute_title_input_hint,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
    option_id,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _, translate_to_current_language

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import InvalidElementMode
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    IncomingData,
    InvalidValue,
    RawDiskData,
    RawFrontendData,
)

T = TypeVar("T")

NO_SELECTION = None


@dataclass
class _FallbackModel(Generic[T]):
    value: str | None
    available_elements: Sequence[private.SingleChoiceElementExtended[T]]


@dataclass
class _ToleratedValue(Generic[T]):
    value: object
    available_elements: Sequence[private.SingleChoiceElementExtended[T]]


@dataclass
class _ValidValue(Generic[T]):
    value: object
    available_elements: Sequence[private.SingleChoiceElementExtended[T]]


_ParsedValueModel: TypeAlias = _ToleratedValue[T] | _ValidValue[T]


class SingleChoiceVisitor(
    Generic[T],
    FormSpecVisitor[private.SingleChoiceExtended[T], _ParsedValueModel[T], _FallbackModel[T]],
):
    @staticmethod
    def _is_valid_choice(
        value: object, elements: Sequence[private.SingleChoiceElementExtended[T]]
    ) -> TypeGuard[T]:
        if isinstance(value, InvalidValue):
            return False
        if not elements:
            return False
        return value in [x.name for x in elements]

    @classmethod
    def option_id(cls, val: object) -> str:
        return option_id(val)

    def _get_elements(self) -> Sequence[private.SingleChoiceElementExtended[T]]:
        if callable(self.form_spec.elements):
            # Lazy evaluation of elements
            return self.form_spec.elements()
        return self.form_spec.elements

    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel[T] | InvalidValue[_FallbackModel[T]]:
        elements = self._get_elements()
        no_selection_fallback: _FallbackModel[T] = _FallbackModel(NO_SELECTION, elements)
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(
                    self.form_spec.prefill, fallback_value=no_selection_fallback
                ),
                InvalidValue,
            ):
                return InvalidValue(
                    reason=self._compute_invalid_value_display_message(DEFAULT_VALUE),
                    fallback_value=prefill_default.fallback_value,
                )
            value: RawFrontendData | RawDiskData = RawFrontendData(self.option_id(prefill_default))
        else:
            value = raw_value

        if isinstance(value, RawFrontendData):
            # Decode option send from frontend
            for option in elements:
                if self.option_id(option.name) == value.value:
                    value = RawDiskData(option.name)
                    break
            else:
                # Found no matching option
                return InvalidValue(
                    reason=self._compute_invalid_value_display_message(value.value),
                    fallback_value=no_selection_fallback,
                )

        if not self._is_valid_choice(value.value, elements):
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
                # The value is tolerated -> not an InvalidValue
                # Tolerated values might be written back to disk
                return _ToleratedValue(value.value, elements)
            return InvalidValue(
                reason=self._compute_invalid_value_display_message(value.value),
                fallback_value=no_selection_fallback,
            )

        return _ValidValue(value.value, elements)

    def _to_vue(
        self, parsed_value: _ParsedValueModel[T] | InvalidValue[_FallbackModel[T]]
    ) -> tuple[shared_type_defs.SingleChoice, str | None]:
        title, help_text = get_title_and_help(self.form_spec)

        elements = [
            shared_type_defs.SingleChoiceElement(
                name=self.option_id(element.name),
                title=element.title.localize(translate_to_current_language),
            )
            for element in (
                parsed_value.fallback_value.available_elements
                if isinstance(parsed_value, InvalidValue)
                else parsed_value.available_elements
            )
        ]

        input_hint = compute_title_input_hint(self.form_spec.prefill)
        # Check if the value was tolerated (invalid choice, but kept due to InvalidElementMode.KEEP)
        if isinstance(parsed_value, _ToleratedValue):
            parsed_value = InvalidValue(
                reason=self._compute_invalid_value_display_message(parsed_value.value),
                fallback_value=_FallbackModel(NO_SELECTION, parsed_value.available_elements),
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
                frozen=self.form_spec.frozen and isinstance(parsed_value, _ValidValue),
                input_hint=input_hint or _("Please choose"),
                no_elements_text=localize(self.form_spec.no_elements_text),
                i18n_base=base_i18n_form_spec(),
            ),
            parsed_value.fallback_value.value
            if isinstance(parsed_value, InvalidValue)
            else self.option_id(parsed_value.value),
        )

    def _compute_invalid_value_display_message(self, invalid_value: object) -> str:
        # Note: The InvalidElementValidator class offers an error_message and a "display" message
        #       On error, the "display" message is shown as dropdown choice input hint
        message = (
            self.form_spec.invalid_element_validation
            and self.form_spec.invalid_element_validation.error_msg
        ) or Message("Invalid choice %r")
        message_localized = localize(message)
        if "%s" in message_localized or "%r" in message_localized:
            if invalid_value == NO_SELECTION:
                return message_localized.replace("%s", "").replace("%r", "")
            return message_localized % (invalid_value,)
        return message_localized

    def _validate(
        self, parsed_value: _ParsedValueModel[T]
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, _ToleratedValue):
            # The value was tolerated (invalid choice, but kept due to InvalidElementMode.KEEP)
            return create_validation_error(
                NO_SELECTION, self._compute_invalid_value_display_message(parsed_value.value)
            )
        return []

    def _to_disk(self, parsed_value: _ParsedValueModel[T]) -> object:
        return parsed_value.value
