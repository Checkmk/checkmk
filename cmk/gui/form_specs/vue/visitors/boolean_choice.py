#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import BooleanChoice

from ._base import FormSpecVisitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue, Value
from ._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_title_and_help,
    localize,
)


class BooleanChoiceVisitor(FormSpecVisitor[BooleanChoice, bool]):
    def _parse_value(self, raw_value: object) -> bool | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            return self.form_spec.prefill.value

        if not isinstance(raw_value, bool):
            return EMPTY_VALUE
        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: bool | EmptyValue
    ) -> tuple[shared_type_defs.BooleanChoice, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.BooleanChoice(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                text_on=localize(Label("on")),
                text_off=localize(Label("off")),
            ),
            parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: bool | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if raw_value == DEFAULT_VALUE else raw_value, Title("Invalid boolean choice")
            )
        return compute_validation_errors(compute_validators(self.form_spec), raw_value)

    def _to_disk(self, raw_value: object, parsed_value: bool | EmptyValue) -> bool:
        if isinstance(parsed_value, EmptyValue):
            raise MKGeneralException("Unable to serialize empty value")
        return parsed_value
