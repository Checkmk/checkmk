#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Optional, Protocol, Sequence

from cmk.gui.form_specs.private.definitions import UnknownFormSpec
from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import (
    form_specs_recomposer_registry,
    form_specs_visitor_registry,
    FormSpecVisitor,
    InputHintValue,
    InvalidValue,
    ParsedValue,
    RecomposerFunction,
    ValidValue,
)
from cmk.gui.form_specs.vue.type_defs import DataOrigin, DEFAULT_VALUE, VisitorOptions
from cmk.gui.i18n import translate_to_current_language

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import DefaultValue, InputHint, ModelT, Prefill
from cmk.rulesets.v1.form_specs.validators import ValidationError


def get_title_and_help(form_spec: FormSpec) -> tuple[str, str]:
    return localize(form_spec.title), localize(form_spec.help_text)


class SupportsLocalize(Protocol):
    def localize(self, localizer: Callable[[str], str]) -> str: ...


def localize(localizable: Optional[SupportsLocalize]) -> str:
    return "" if localizable is None else localizable.localize(translate_to_current_language)


def get_visitor(form_spec: FormSpec, options: VisitorOptions) -> FormSpecVisitor:
    # Decompose the form spec into simpler types, if necessary
    if decomposer := form_specs_recomposer_registry.get(form_spec.__class__):
        form_spec = decomposer(form_spec)

    # If the form spec still has no valid visitor, convert it to the legacy valuespec visitor
    if form_spec.__class__ not in form_specs_visitor_registry:
        unknown_decomposer = form_specs_recomposer_registry.get(UnknownFormSpec)
        assert unknown_decomposer is not None
        form_spec = unknown_decomposer(form_spec)

    if visitor := form_specs_visitor_registry.get(form_spec.__class__):
        return visitor(form_spec, options)
    raise MKGeneralException(f"Cannot find visitor for form spec {form_spec}")


def optional_validation(
    validators: Sequence[Callable[[ModelT], object]], raw_value: Any
) -> list[str]:
    validation_errors = []
    for validator in validators:
        try:
            validator(raw_value)
        except ValidationError as e:
            validation_errors.append(e.message.localize(translate_to_current_language))
            # The aggregated errors are used within our old GUI which
            # requires the MKUser error format (field_id + message)
            # self._aggregated_validation_errors.add(e.message)
            # TODO: add external validation errors for legacy formspecs
            #       or handle it within the form_spec_valuespec_wrapper
    return validation_errors


def register_visitor_class(
    form_spec_class: type[FormSpec], visitor_class: type[FormSpecVisitor]
) -> None:
    form_specs_visitor_registry[form_spec_class] = visitor_class


def register_form_spec_recomposer(
    form_spec_class: type[FormSpec], decomposer: RecomposerFunction
) -> None:
    form_specs_recomposer_registry[form_spec_class] = decomposer


def create_validation_error(value: InvalidValue) -> list[VueComponents.ValidationMessage]:
    return [
        VueComponents.ValidationMessage(
            location=[], message=value.error_message, invalid_value=value.invalid_value
        )
    ]


def compute_validation_errors(
    validators: Sequence[Callable[[ModelT], object]],
    raw_value: Any,
) -> list[VueComponents.ValidationMessage]:
    return [
        VueComponents.ValidationMessage(location=[], message=x, invalid_value=raw_value)
        for x in optional_validation(validators, raw_value)
        if x is not None
    ]


def compute_valid_value(value: ParsedValue, default: Any) -> Any:
    return value.value if isinstance(value, ValidValue) else default


def migrate_value(form_spec: FormSpec, options: VisitorOptions, value: Any) -> Any:
    if (
        not isinstance(value, DEFAULT_VALUE)
        and options.data_origin == DataOrigin.DISK
        and form_spec.migrate
    ):
        return form_spec.migrate(value)
    return value


class WithPrefill(Protocol[ModelT]):
    @property
    def prefill(
        self,
    ) -> Prefill[ModelT]: ...


def process_prefills(form_spec: WithPrefill, value: ModelT | DEFAULT_VALUE) -> tuple[ModelT, bool]:
    if not isinstance(value, DEFAULT_VALUE):
        return value, False

    return form_spec.prefill.value, isinstance(form_spec.prefill, InputHint)


class WithPrefillTitle(Protocol[ModelT]):
    @property
    def prefill(self) -> DefaultValue[ModelT] | InputHint[Title]: ...


def process_prefills_with_title(
    form_spec: WithPrefillTitle, value: ModelT | DEFAULT_VALUE
) -> tuple[ModelT | str, bool]:
    if not isinstance(value, DEFAULT_VALUE):
        return value, False

    if isinstance(form_spec.prefill, InputHint):
        return form_spec.prefill.value.localize(translate_to_current_language), True
    return form_spec.prefill.value, False


def compute_parsed_value(
    value: Any, is_input_hint: bool, value_type: type[ModelT]
) -> ParsedValue[ModelT]:
    if not isinstance(value, value_type):
        return InvalidValue(
            invalid_value=repr(value), error_message=f"Expected a {value_type}, got {type(value)}"
        )

    if is_input_hint:
        return InputHintValue[ModelT](value=value)
    return ValidValue[ModelT](value=value)


def compute_input_hint(form_spec: WithPrefill | WithPrefillTitle) -> ModelT | None | str:
    if isinstance(form_spec.prefill, InputHint):
        if isinstance(form_spec.prefill.value, Title):
            return form_spec.prefill.value.localize(translate_to_current_language)
        return form_spec.prefill.value
    return None


def compute_text_input_value(parsed_value: ParsedValue) -> ModelT | str:
    if isinstance(parsed_value, InputHintValue):
        return ""
    if isinstance(parsed_value, ValidValue):
        return parsed_value.value
    return parsed_value.invalid_value
