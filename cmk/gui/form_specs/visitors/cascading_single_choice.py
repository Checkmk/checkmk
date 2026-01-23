#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import override

from cmk.gui.form_specs.unstable import CascadingSingleChoiceExtended
from cmk.gui.i18n import _, translate_to_current_language
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    IncomingData,
    InvalidValue,
    RawDiskData,
    RawFrontendData,
)
from ._utils import (
    compute_label,
    compute_title_input_hint,
    compute_validators,
    get_prefill_default,
    get_title_and_help,
    localize,
)
from .validators import build_vue_validators

_ParsedValueModel = tuple[str, IncomingData]
_FallbackModel = tuple[str, DefaultValue]


class CascadingSingleChoiceVisitor(
    FormSpecVisitor[CascadingSingleChoiceExtended, _ParsedValueModel, _FallbackModel]
):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            fallback_value: _FallbackModel = ("", DEFAULT_VALUE)
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill, fallback_value),
                InvalidValue,
            ):
                return prefill_default
            # The default value for a cascading_single_choice element only
            # contains the name of the selected element, not the value.
            return (prefill_default, DEFAULT_VALUE)
        if not isinstance(raw_value.value, list | tuple) or len(raw_value.value) != 2:
            return InvalidValue(reason=_("Invalid datatype"), fallback_value=("", DEFAULT_VALUE))

        name = raw_value.value[0]
        if not any(name == element.name for element in self.form_spec.elements):
            return InvalidValue(reason=_("Invalid selection"), fallback_value=("", DEFAULT_VALUE))

        assert isinstance(name, str)
        if isinstance(raw_value, RawDiskData):
            return (name, RawDiskData(raw_value.value[1]))
        else:
            return (name, RawFrontendData(raw_value.value[1]))

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.CascadingSingleChoice, object]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, InvalidValue):
            parsed_value = parsed_value.fallback_value

        selected_name, selected_value = parsed_value
        selected_vue_value: object = None
        vue_elements = []

        for element in self.form_spec.elements:
            element_visitor = get_visitor(element.parameter_form, self.visitor_options)
            element_value = selected_value if selected_name == element.name else DEFAULT_VALUE
            element_schema, element_vue_value = element_visitor.to_vue(element_value)

            if selected_name == element.name:
                selected_vue_value = element_vue_value

            vue_elements.append(
                shared_type_defs.CascadingSingleChoiceElement(
                    name=element.name,
                    title=element.title.localize(translate_to_current_language),
                    default_value=element_vue_value,
                    parameter_form=element_schema,
                )
            )

        return (
            shared_type_defs.CascadingSingleChoice(
                title=title,
                label=compute_label(self.form_spec.label),
                help=help_text,
                elements=vue_elements,
                no_elements_text=localize(self.form_spec.no_elements_text),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                input_hint=compute_title_input_hint(self.form_spec.prefill),
                layout=self.form_spec.layout,
            ),
            (selected_name, selected_vue_value),
        )

    @override
    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        selected_name, selected_value = parsed_value

        element_validations: list[shared_type_defs.ValidationMessage] = []
        for element in self.form_spec.elements:
            if selected_name != element.name:
                continue

            element_visitor = get_visitor(element.parameter_form, self.visitor_options)
            for validation in element_visitor.validate(selected_value):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[element.name] + validation.location,
                        message=validation.message,
                        replacement_value=validation.replacement_value,
                    )
                )

        return element_validations

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> tuple[str, object]:
        selected_name, selected_value = parsed_value

        disk_value: object = None
        for element in self.form_spec.elements:
            if selected_name != element.name:
                continue
            element_visitor = get_visitor(element.parameter_form, self.visitor_options)
            disk_value = element_visitor.to_disk(selected_value)
        return selected_name, disk_value
