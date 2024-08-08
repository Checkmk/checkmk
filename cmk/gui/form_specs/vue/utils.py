#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Optional, Protocol, Sequence

from cmk.gui.form_specs.private.definitions import UnknownFormSpec
from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import (
    form_specs_visitor_registry,
    FormSpecVisitor,
    RecomposerFunction,
)
from cmk.gui.form_specs.vue.type_defs import DataOrigin
from cmk.gui.form_specs.vue.type_defs import DefaultValue as FormSpecDefaultValue
from cmk.gui.form_specs.vue.type_defs import EMPTY_VALUE, EmptyValue, VisitorOptions
from cmk.gui.htmllib import html
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.utils import escaping

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import DefaultValue, InputHint, ModelT
from cmk.rulesets.v1.form_specs.validators import ValidationError


def get_title_and_help(form_spec: FormSpec[ModelT]) -> tuple[str, str]:
    title_text = localize(form_spec.title)
    translated_help_text = localize(form_spec.help_text)
    escaped_help_text = escaping.escape_to_html_permissive(translated_help_text, escape_links=False)
    return title_text, html.HTMLGenerator.resolve_help_text_macros(str(escaped_help_text))


class SupportsLocalize(Protocol):
    def localize(self, localizer: Callable[[str], str]) -> str: ...


def localize(localizable: Optional[SupportsLocalize]) -> str:
    return "" if localizable is None else localizable.localize(translate_to_current_language)


def get_visitor(
    form_spec: FormSpec[ModelT], options: VisitorOptions
) -> FormSpecVisitor[FormSpec[ModelT], ModelT]:
    if registered_form_spec := form_specs_visitor_registry.get(form_spec.__class__):
        visitor, recomposer_function = registered_form_spec
        if recomposer_function is not None:
            form_spec = recomposer_function(form_spec)
        return visitor(form_spec, options)

    # If the form spec has no valid visitor, convert it to the legacy valuespec visitor
    visitor, unknown_decomposer = form_specs_visitor_registry[UnknownFormSpec]
    assert unknown_decomposer is not None
    return visitor(unknown_decomposer(form_spec), options)


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
    form_spec_class: type[FormSpec[ModelT]],
    visitor_class: type[FormSpecVisitor[Any, ModelT]],
    recomposer: RecomposerFunction | None = None,
) -> None:
    form_specs_visitor_registry[form_spec_class] = (visitor_class, recomposer)


def create_validation_error(
    value: object, error_message: Title | str
) -> list[VueComponents.ValidationMessage]:
    if isinstance(error_message, Title):
        error_message = error_message.localize(translate_to_current_language)
    return [
        VueComponents.ValidationMessage(location=[], message=error_message, invalid_value=value)
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


def compute_validators(form_spec: FormSpec[ModelT]) -> list[Callable[[ModelT], object]]:
    return list(form_spec.custom_validate) if form_spec.custom_validate else []


def migrate_value(form_spec: FormSpec[ModelT], options: VisitorOptions, value: Any) -> Any:
    if (
        not isinstance(value, FormSpecDefaultValue)
        and options.data_origin == DataOrigin.DISK
        and form_spec.migrate
    ):
        return form_spec.migrate(value)
    return value


_PrefillTypes = DefaultValue[ModelT] | InputHint[ModelT] | InputHint[Title]


def get_prefill_default(prefill: _PrefillTypes[ModelT]) -> ModelT | EmptyValue:
    if not isinstance(prefill, DefaultValue):
        return EMPTY_VALUE
    return prefill.value


def compute_text_input_hint(prefill: _PrefillTypes[ModelT]) -> str | None:
    if not isinstance(prefill, InputHint):
        return None

    if isinstance(prefill.value, Title):
        return prefill.value.localize(translate_to_current_language)
    return str(prefill.value)


def compute_label(label: Label | None) -> str | None:
    if label is None:
        return None
    return label.localize(translate_to_current_language)
