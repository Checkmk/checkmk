#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Generic, override, TypeVar

from cmk.gui.i18n import _, translate_to_current_language
from cmk.rulesets.internal.form_specs import ListExtended
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
from ._utils import compute_validators, get_title_and_help
from .validators import build_vue_validators

T = TypeVar("T")

_ParsedValueModel = Sequence[IncomingData]
_FallbackModel = Sequence[RawFrontendData]


class ListVisitor(
    Generic[T],
    FormSpecVisitor[ListExtended[T], _ParsedValueModel, _FallbackModel],
):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return [RawDiskData(v) for v in self.form_spec.prefill.value]

        if not isinstance(raw_value.value, list):
            return InvalidValue(reason=_("Invalid data"), fallback_value=[])

        return [
            RawDiskData(v) if isinstance(raw_value, RawDiskData) else RawFrontendData(v)
            for v in raw_value.value
        ]

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.List, object]:
        if isinstance(parsed_value, InvalidValue):
            parsed_value = parsed_value.fallback_value

        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self.form_spec.element_template, self.visitor_options)
        element_schema, element_vue_default_value = element_visitor.to_vue(DEFAULT_VALUE)
        list_values: list[object] = []
        for entry in parsed_value:
            # Note: InputHints are not really supported for list elements
            #       We just collect data for a given template
            #       The data cannot be a mixture between values and InputHint
            _spec, element_vue_value = element_visitor.to_vue(entry)
            list_values.append(element_vue_value)

        return (
            shared_type_defs.List(
                title=title,
                help=help_text,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                element_template=element_schema,
                element_default_value=element_vue_default_value,
                add_element_label=self.form_spec.add_element_label.localize(
                    translate_to_current_language
                ),
                remove_element_label=self.form_spec.remove_element_label.localize(
                    translate_to_current_language
                ),
                no_element_label=self.form_spec.no_element_label.localize(
                    translate_to_current_language
                ),
                editable_order=self.form_spec.editable_order,
            ),
            list_values,
        )

    @override
    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        element_validations: list[shared_type_defs.ValidationMessage] = []
        element_visitor = get_visitor(self.form_spec.element_template, self.visitor_options)
        for idx, entry in enumerate(parsed_value):
            for validation in element_visitor.validate(entry):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[str(idx)] + list(validation.location),
                        message=validation.message,
                        replacement_value=validation.replacement_value,
                    )
                )
        return element_validations

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> list[object]:
        disk_values = []
        element_visitor = get_visitor(self.form_spec.element_template, self.visitor_options)
        for entry in parsed_value:
            disk_values.append(element_visitor.to_disk(entry))
        return disk_values
