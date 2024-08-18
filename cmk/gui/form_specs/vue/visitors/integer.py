#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence

from cmk.gui.form_specs.private.validators import IsInteger
from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import DefaultValue, EMPTY_VALUE, EmptyValue
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

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Integer


class IntegerVisitor(FormSpecVisitor[Integer, int]):
    def _parse_value(self, raw_value: object) -> int | EmptyValue:
        raw_value = migrate_value(self.form_spec, self.options, raw_value)
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default

        #  23 / -23 / "23" / "-23" -> OK
        #  23.0 / "23.0" / other   -> EMPTY_VALUE
        if not isinstance(raw_value, int):
            return EMPTY_VALUE
        try:
            return int(raw_value)
        except ValueError:
            return EMPTY_VALUE

    def _validators(self) -> Sequence[Callable[[int], object]]:
        return [IsInteger()] + compute_validators(self.form_spec)

    def _to_vue(
        self, raw_value: object, parsed_value: int | EmptyValue
    ) -> tuple[VueComponents.Integer, str | int]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            VueComponents.Integer(
                title=title,
                help=help_text,
                unit=self.form_spec.unit_symbol,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=compute_text_input_hint(self.form_spec.prefill),
            ),
            "" if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: int | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if isinstance(raw_value, DefaultValue) else raw_value,
                Title("Invalid integer number"),
            )
        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: int) -> int:
        return parsed_value
