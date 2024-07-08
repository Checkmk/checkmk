#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Callable, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DataForDisk,
    DataOrigin,
    DEFAULT_VALUE,
    Value,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import compute_validation_errors, get_title_and_help
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1.form_specs import InputHint, SingleChoice


class SingleChoiceVisitor(FormSpecVisitor):
    def __init__(self, form_spec: SingleChoice, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[str], object]]:
        # TODO: add special __post_init__ / ignored_elements / invalid element
        #      validators for this form spec
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> str:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            if isinstance(self.form_spec.prefill, InputHint):
                value = ""
            else:
                value = self.form_spec.prefill.value

        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value)}")

        return value

    def to_vue(self, value: str) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        elements = [
            VueComponents.SingleChoiceElement(
                name=element.name,
                title=element.title.localize(translate_to_current_language),
            )
            for element in self.form_spec.elements
        ]
        return (
            VueComponents.SingleChoice(
                title=title,
                help=help_text,
                elements=elements,
                validators=build_vue_validators(self._validators()),
                frozen=self.form_spec.frozen,
            ),
            value,
        )

    def validate(self, value: str) -> list[VueComponents.ValidationMessage]:
        return compute_validation_errors(self._validators(), value)

    def to_disk(self, value: str) -> DataForDisk:
        return value
