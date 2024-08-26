#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import MultilineText

from ._base import FormSpecVisitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue, Value
from ._utils import (
    compute_label,
    compute_text_input_hint,
    compute_validation_errors,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
)


class MultilineTextVisitor(FormSpecVisitor[MultilineText, str]):
    def _parse_value(self, raw_value: object) -> str | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, str):
            return EMPTY_VALUE
        return raw_value

    def _validators(self) -> Sequence[Callable[[str], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def _to_vue(
        self, raw_value: object, parsed_value: str | EmptyValue
    ) -> tuple[shared_type_defs.MultilineText, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.MultilineText(
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                input_hint=compute_text_input_hint(self.form_spec.prefill),
                monospaced=self.form_spec.monospaced,
                macro_support=self.form_spec.macro_support,
                label=compute_label(self.form_spec.label),
            ),
            "" if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: str | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if raw_value == DEFAULT_VALUE else raw_value, Title("Invalid text")
            )
        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: str) -> str:
        return parsed_value
