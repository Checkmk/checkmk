#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import assert_never

from cmk.gui.form_specs.converter import Tuple
from cmk.gui.form_specs.vue._utils import compute_validators, get_title_and_help
from cmk.gui.form_specs.vue._visitor_base import FormSpecVisitor
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _

from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._registry import get_visitor
from .._type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    IncomingData,
    InvalidValue,
    RawDiskData,
    RawFrontendData,
)

_ParsedValueModel = tuple[IncomingData, ...]
_FallbackModel = list[IncomingData]


class TupleVisitor(FormSpecVisitor[Tuple, _ParsedValueModel, _FallbackModel]):
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return (DEFAULT_VALUE,) * len(self.form_spec.elements)

        if not isinstance(raw_value.value, list | tuple):
            return InvalidValue(
                reason=_("Invalid tuple"),
                fallback_value=[
                    DEFAULT_VALUE,
                ]
                * len(self.form_spec.elements),
            )

        if len(raw_value.value) != len(self.form_spec.elements):
            return InvalidValue(
                reason=_("Invalid number of tuple elements"),
                fallback_value=[
                    DEFAULT_VALUE,
                ]
                * len(self.form_spec.elements),
            )

        match raw_value:
            case RawFrontendData():
                return tuple(RawFrontendData(v) for v in raw_value.value)
            case RawDiskData():
                return tuple(RawDiskData(v) for v in raw_value.value)
            case other:
                assert_never(other)

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.Tuple, object]:
        title, help_text = get_title_and_help(self.form_spec)
        vue_specs = []
        vue_elements: list[object] = []

        tuple_values: Sequence[IncomingData]
        if isinstance(parsed_value, InvalidValue):
            tuple_values = parsed_value.fallback_value
        else:
            tuple_values = parsed_value

        for element_spec, value in zip(self.form_spec.elements, tuple_values):
            element_vue, element_value = get_visitor(element_spec).to_vue(value)
            vue_specs.append(element_vue)
            vue_elements.append(element_value)

        return (
            shared_type_defs.Tuple(
                title=title,
                help=help_text,
                elements=vue_specs,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                layout=shared_type_defs.TupleLayout(self.form_spec.layout),
                show_titles=self.form_spec.show_titles,
            ),
            vue_elements,
        )

    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        validation_errors: list[shared_type_defs.ValidationMessage] = []
        for idx, (element_spec, value) in enumerate(zip(self.form_spec.elements, parsed_value)):
            element_visitor = get_visitor(element_spec)
            for validation in element_visitor.validate(value):
                validation_errors.append(
                    shared_type_defs.ValidationMessage(
                        location=[str(idx)] + validation.location,
                        message=validation.message,
                        replacement_value=validation.replacement_value,
                    )
                )
        return validation_errors

    def _to_disk(self, parsed_value: _ParsedValueModel) -> tuple[object, ...]:
        disk_values = []
        for parameter_form, value in zip(self.form_spec.elements, parsed_value, strict=True):
            element_visitor = get_visitor(parameter_form)
            disk_values.append(element_visitor.to_disk(value))
        return tuple(disk_values)
