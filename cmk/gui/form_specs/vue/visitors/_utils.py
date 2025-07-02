#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import hashlib
from collections.abc import Callable, Sequence
from typing import Any, Protocol, TypeVar

from cmk.gui.form_specs.vue.visitors._type_defs import InvalidValue
from cmk.gui.htmllib import html
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.utils import escaping

from cmk.rulesets.v1 import Label, Message, Title
from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec, InputHint, Prefill
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing import vue_formspec_components as shared_type_defs

ModelT = TypeVar("ModelT")


def get_title_and_help(form_spec: FormSpec[ModelT]) -> tuple[str, str]:
    title_text = localize(form_spec.title)
    translated_help_text = localize(form_spec.help_text)
    escaped_help_text = escaping.escape_to_html_permissive(translated_help_text, escape_links=False)
    return title_text, html.HTMLGenerator.resolve_help_text_macros(str(escaped_help_text))


class SupportsLocalize(Protocol):
    def localize(self, localizer: Callable[[str], str]) -> str: ...


def localize(localizable: SupportsLocalize | None) -> str:
    return "" if localizable is None else localizable.localize(translate_to_current_language)


def base_i18n_form_spec() -> shared_type_defs.I18nFormSpecBase:
    return shared_type_defs.I18nFormSpecBase(required=_("required"))


def optional_validation(
    validators: Sequence[Callable[[ModelT], object]], raw_value: Any
) -> list[str]:
    validation_errors = []
    for validator in validators:
        try:
            validator(raw_value)
        except ValidationError as e:
            validation_errors.append(e.message.localize(translate_to_current_language))
    return validation_errors


def create_validation_error(
    value: object, error_message: Title | Message | str, location: list[str] | None = None
) -> list[shared_type_defs.ValidationMessage]:
    if isinstance(error_message, Title | Message):
        error_message = error_message.localize(translate_to_current_language)
    return [
        shared_type_defs.ValidationMessage(
            location=location or [], message=error_message, replacement_value=value
        )
    ]


def compute_validation_errors(
    validators: Sequence[Callable[[ModelT], object]],
    replacement_value: Any,
    raw_value: Any,
) -> list[shared_type_defs.ValidationMessage]:
    return [
        shared_type_defs.ValidationMessage(
            location=[], message=x, replacement_value=replacement_value
        )
        for x in optional_validation(validators, raw_value)
        if x is not None
    ]


def compute_validators(form_spec: FormSpec[Any]) -> list[Callable[[Any], object]]:
    return list(form_spec.custom_validate) if form_spec.custom_validate else []


_PrefillTypes = DefaultValue[ModelT] | InputHint[ModelT] | InputHint[Title]
_InvalidValueModel = TypeVar("_InvalidValueModel")


def get_prefill_default(
    prefill: _PrefillTypes[ModelT], fallback_value: _InvalidValueModel
) -> ModelT | InvalidValue[_InvalidValueModel]:
    if not isinstance(prefill, DefaultValue):
        return InvalidValue[_InvalidValueModel](
            reason=_("Prefill value is an input hint"), fallback_value=fallback_value
        )
    return prefill.value


def compute_title_input_hint(prefill: DefaultValue[ModelT] | InputHint[Title]) -> str | None:
    # InputHint[Title] is only used by SingleChoice and CascadingSingleChoice
    # in all other cases you should use compute_input_hint
    if isinstance(prefill, InputHint):
        return prefill.value.localize(translate_to_current_language)

    return None


def compute_input_hint(prefill: Prefill[ModelT]) -> ModelT | None:
    if not isinstance(prefill, InputHint):
        return None
    return prefill.value


def compute_label(label: Label | None) -> str | None:
    if label is None:
        return None
    return label.localize(translate_to_current_language)


def option_id(val: object) -> str:
    return "%s" % hashlib.sha256(repr(val).encode()).hexdigest()
