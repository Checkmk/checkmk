#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import cast, Generic, TypeVar

from cmk.gui.form_specs.private import CascadingSingleChoiceExtended, SingleChoiceExtended
from cmk.gui.form_specs.private.list_unique_selection import (
    ListUniqueSelection,
    UniqueCascadingSingleChoiceElement,
    UniqueSingleChoiceElement,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _, translate_to_current_language

from cmk.rulesets.v1.form_specs import CascadingSingleChoice, FormSpec, SingleChoice
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, InvalidValue
from ._utils import compute_validators, get_title_and_help, option_id

T = TypeVar("T")

_ParsedValueModel = Sequence[T]
_FrontendModel = Sequence[T]


class ListUniqueSelectionVisitor(
    Generic[T],
    FormSpecVisitor[ListUniqueSelection[T], _ParsedValueModel[T], _FrontendModel[T]],
):
    def _parse_value(
        self, raw_value: object
    ) -> _ParsedValueModel[T] | InvalidValue[_FrontendModel[T]]:
        if isinstance(raw_value, DefaultValue):
            return self.form_spec.prefill.value

        if not isinstance(raw_value, list):
            return InvalidValue(reason=_("Invalid data"), fallback_value=[])
        return raw_value

    def _to_vue(
        self, parsed_value: _ParsedValueModel[T] | InvalidValue[_FrontendModel[T]]
    ) -> tuple[shared_type_defs.ListUniqueSelection, _FrontendModel[T]]:
        if isinstance(parsed_value, InvalidValue):
            parsed_value = parsed_value.fallback_value

        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self._build_element_template(), self.options)
        element_schema, element_vue_default_value = element_visitor.to_vue(DEFAULT_VALUE)

        list_values: list[T] = []
        for entry in parsed_value:
            # Note: InputHints are not really supported for list elements
            #       We just collect data for a given template
            #       The data cannot be a mixture between values and InputHint
            _spec, element_vue_value = element_visitor.to_vue(entry)
            list_values.append(cast(T, element_vue_value))

        assert isinstance(
            element_schema,
            shared_type_defs.SingleChoice | shared_type_defs.CascadingSingleChoice,
        )
        return (
            shared_type_defs.ListUniqueSelection(
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
                unique_selection_elements=self._build_unique_selection_elements(),
            ),
            list_values,
        )

    def _build_unique_selection_elements(self) -> list[str]:
        if self.form_spec.single_choice_type is SingleChoice:
            return [
                option_id(element.parameter_form.name)
                for element in self.form_spec.elements
                if element.unique
            ]
        if self.form_spec.single_choice_type is CascadingSingleChoice:
            return [
                element.parameter_form.name for element in self.form_spec.elements if element.unique
            ]
        raise ValueError("Invalid single_choice_type")

    def _build_element_template(self) -> FormSpec[T]:
        if self.form_spec.single_choice_type is SingleChoice:
            return SingleChoiceExtended(
                elements=[
                    element.parameter_form
                    for element in self.form_spec.elements
                    if isinstance(element, UniqueSingleChoiceElement)
                ],
                label=self.form_spec.single_choice_label,
                prefill=self.form_spec.single_choice_prefill,
            )
        if self.form_spec.single_choice_type is CascadingSingleChoice:
            return CascadingSingleChoiceExtended(  # type: ignore[return-value]
                elements=[
                    element.parameter_form
                    for element in self.form_spec.elements
                    if isinstance(element, UniqueCascadingSingleChoiceElement)
                ],
                label=self.form_spec.single_choice_label,
                prefill=self.form_spec.single_choice_prefill,
                layout=self.form_spec.cascading_single_choice_layout,
            )
        raise ValueError("Invalid single_choice_type")

    def _validate(
        self, parsed_value: _ParsedValueModel[T]
    ) -> list[shared_type_defs.ValidationMessage]:
        element_validations: list[shared_type_defs.ValidationMessage] = []
        element_visitor = get_visitor(self._build_element_template(), self.options)

        for idx, entry in enumerate(parsed_value):
            for validation in element_visitor.validate(entry):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[str(idx)] + validation.location,
                        message=validation.message,
                        replacement_value=validation.replacement_value,
                    )
                )
        return element_validations

    def _to_disk(self, parsed_value: _ParsedValueModel[T]) -> list[T]:
        disk_values = []
        element_visitor = get_visitor(self._build_element_template(), self.options)
        for entry in parsed_value:
            disk_values.append(element_visitor.to_disk(entry))
        return disk_values
