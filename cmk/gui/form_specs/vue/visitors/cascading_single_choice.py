#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import (
    FormSpecVisitor,
    InputHintValue,
    InvalidValue,
    ParsedValue,
    ValidateValue,
    ValidValue,
)
from cmk.gui.form_specs.vue.type_defs import default_value, DEFAULT_VALUE, Value, VisitorOptions
from cmk.gui.form_specs.vue.utils import (
    compute_input_hint,
    compute_parsed_value,
    compute_valid_value,
    compute_validation_errors,
    create_validation_error,
    get_title_and_help,
    get_visitor,
    migrate_value,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import CascadingSingleChoice, DefaultValue


class CascadingSingleChoiceVisitor(FormSpecVisitor):
    def __init__(self, form_spec: CascadingSingleChoice, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[tuple[str, object]], object]]:
        # TODO: add special __post_init__ / element validators for this form spec
        return self.form_spec.custom_validate if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> ParsedValue[list]:
        value = migrate_value(self.form_spec, self.options, value)
        if isinstance(value, DEFAULT_VALUE):
            # The default value for a cascading_single_choice only contains the name
            if isinstance(self.form_spec.prefill, DefaultValue):
                selected_default = self.form_spec.prefill.value
                selected_value = default_value
                return ValidValue(value=[selected_default, selected_value])
            return InputHintValue(value=[])
        # TODO: this type argument is not complete
        if isinstance(value, tuple):
            value = list(value)
        return compute_parsed_value(value, False, list)

    def to_vue(
        self, parsed_value: ParsedValue[list]
    ) -> tuple[VueComponents.CascadingSingleChoice, Value]:
        title, help_text = get_title_and_help(self.form_spec)

        selected_name, selected_value = compute_valid_value(parsed_value, ("", None))

        vue_elements = []
        for element in self.form_spec.elements:
            element_visitor = get_visitor(element.parameter_form, self.options)
            element_parsed_value = element_visitor.parse_value(
                default_value if selected_name != element.name else selected_value
            )
            element_schema, element_vue_value = element_visitor.to_vue(element_parsed_value)

            if selected_name == element.name:
                selected_value = element_vue_value

            vue_elements.append(
                VueComponents.CascadingSingleChoiceElement(
                    name=element.name,
                    title=element.title.localize(translate_to_current_language),
                    default_value=element_vue_value,
                    parameter_form=element_schema,
                )
            )

        return (
            VueComponents.CascadingSingleChoice(
                title=title,
                help=help_text,
                elements=vue_elements,
                validators=build_vue_validators(self._validators()),
                input_hint=compute_input_hint(self.form_spec),
            ),
            (selected_name, selected_value),
        )

    def validate(self, parsed_value: ValidateValue[list]) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(parsed_value)

        value = parsed_value.value
        selected_name, selected_value = value
        element_validations = (
            compute_validation_errors(list(self.form_spec.custom_validate), value)
            if self.form_spec.custom_validate
            else []
        )

        for element in self.form_spec.elements:
            if selected_name != element.name:
                continue

            element_visitor = get_visitor(element.parameter_form, self.options)
            element_parsed_value = element_visitor.parse_value(selected_value)
            if isinstance(element_parsed_value, InputHintValue):
                raise MKGeneralException(f"Cannot validate field {element.name} with InputHint")

            for validation in element_visitor.validate(element_parsed_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[element.name] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )

        return element_validations

    def to_disk(self, parsed_value: ValidValue[list]) -> tuple[str, Any]:
        selected_name, selected_value = parsed_value.value

        disk_value: Any = None
        for element in self.form_spec.elements:
            if selected_name != element.name:
                continue

            element_visitor = get_visitor(element.parameter_form, self.options)
            element_parsed_value = element_visitor.parse_value(selected_value)
            if isinstance(element_parsed_value, (InputHintValue, InvalidValue)):
                raise MKGeneralException(
                    f"Cannot serialize field {element.name} with {type(element_parsed_value)}"
                )
            disk_value = element_visitor.to_disk(element_parsed_value)

        return selected_name, disk_value
