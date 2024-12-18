#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import Literal

from cmk.gui.form_specs.private.validators import IsInteger
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Integer
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, INVALID_VALUE, InvalidValue
from ._utils import (
    base_i18n_form_spec,
    compute_input_hint,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
)


class IntegerVisitor(FormSpecVisitor[Integer, int]):
    def _parse_value(self, raw_value: object) -> int | InvalidValue:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), InvalidValue
            ):
                return prefill_default
            raw_value = prefill_default

        #  23 / -23 / "23" / "-23" -> OK
        #  23.0 / "23.0" / other   -> INVALID
        if not isinstance(raw_value, int):
            return INVALID_VALUE
        try:
            return int(raw_value)
        except ValueError:
            return INVALID_VALUE

    def _validators(self) -> Sequence[Callable[[int], object]]:
        return [IsInteger()] + compute_validators(self.form_spec)

    def _to_vue(
        self, raw_value: object, parsed_value: int | InvalidValue
    ) -> tuple[shared_type_defs.Integer, Literal[""] | int]:
        title, help_text = get_title_and_help(self.form_spec)
        input_hint = compute_input_hint(self.form_spec.prefill)
        input_hint_str = None if input_hint is None else str(input_hint)
        return (
            shared_type_defs.Integer(
                title=title,
                help=help_text,
                unit=self.form_spec.unit_symbol,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=input_hint_str,
                i18n_base=base_i18n_form_spec(),
            ),
            "" if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: int | InvalidValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(
                "" if isinstance(raw_value, DefaultValue) else raw_value,
                Title("Invalid integer number"),
            )
        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: int) -> int:
        return parsed_value
