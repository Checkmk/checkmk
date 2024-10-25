#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
from collections.abc import Mapping

from cmk.ccc.i18n import _

from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended
from cmk.gui.form_specs.vue import shared_type_defs

from cmk.rulesets.v1.form_specs._composed import NoGroup

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DataOrigin, DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_title_and_help,
    localize,
)


class DictionaryVisitor(FormSpecVisitor[DictionaryExtended, Mapping[str, object]]):
    def _compute_default_values(self) -> Mapping[str, object]:
        if self.form_spec.prefill is None:
            return {
                key: DEFAULT_VALUE for key, el in self.form_spec.elements.items() if el.required
            }
        return self.form_spec.prefill.value

    def _get_static_elements(self) -> set[str]:
        return set(self.form_spec.ignored_elements or ())

    def _compute_static_elements(self, parsed_value: Mapping[str, object]) -> dict[str, str]:
        return {x: repr(y) for x, y in parsed_value.items() if x in self._get_static_elements()}

    def _resolve_static_elements(self, raw_value: Mapping[str, object]) -> dict[str, object]:
        # Create a shallow copy, we might modify some of the keys in the raw_value
        value = dict(raw_value)
        if self.options.data_origin == DataOrigin.FRONTEND:
            for ignored_key in self._get_static_elements():
                if ignored_value := value.get(ignored_key):
                    assert isinstance(ignored_value, str)
                    value[ignored_key] = ast.literal_eval(ignored_value)
        return value

    def _has_invalid_keys(self, value: dict[str, object]) -> bool:
        valid_keys = self.form_spec.elements.keys()
        if value.keys() - valid_keys - self._get_static_elements():
            return True
        return False

    def _parse_value(self, raw_value: object) -> dict[str, object] | EmptyValue:
        raw_value = (
            self._compute_default_values() if isinstance(raw_value, DefaultValue) else raw_value
        )
        if not isinstance(raw_value, Mapping):
            return EMPTY_VALUE

        try:
            resolved_dict = self._resolve_static_elements(raw_value)
            if self._has_invalid_keys(resolved_dict):
                return EMPTY_VALUE
            return resolved_dict
        except ValueError:
            return EMPTY_VALUE

    def _to_vue(
        self, raw_value: object, parsed_value: Mapping[str, object] | EmptyValue
    ) -> tuple[shared_type_defs.Dictionary, dict[str, object]]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, EmptyValue):
            # TODO: add warning message somewhere "falling back to defaults"
            parsed_value = self._compute_default_values()

        elements_keyspec = []
        vue_values = {}

        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in parsed_value
            element_value = parsed_value[key_name] if is_active else DEFAULT_VALUE
            element_schema, element_vue_value = element_visitor.to_vue(element_value)

            if isinstance(dict_element.group, NoGroup):
                group = None

            else:
                group = shared_type_defs.DictionaryGroup(
                    title=localize(dict_element.group.title),
                    help=localize(dict_element.group.help_text),
                    key=repr(dict_element.group.title) + repr(dict_element.group.help_text),
                )

            if is_active:
                vue_values[key_name] = element_vue_value

            elements_keyspec.append(
                shared_type_defs.DictionaryElement(
                    ident=key_name,
                    default_value=element_vue_value,
                    required=dict_element.required,
                    parameter_form=element_schema,
                    group=group,
                )
            )

        return (
            shared_type_defs.Dictionary(
                groups=[],
                title=title,
                help=help_text,
                elements=elements_keyspec,
                no_elements_text=localize(self.form_spec.no_elements_text),
                additional_static_elements=self._compute_static_elements(parsed_value),
                layout=self.form_spec.layout,
            ),
            vue_values,
        )

    def _validate(
        self, raw_value: object, parsed_value: Mapping[str, object] | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(raw_value, "Expected a valid value, got EmptyValue")

        # NOTE: the parsed_value may include keys with default values, e.g. {"ce": default_value}
        element_validations = [
            *compute_validation_errors(compute_validators(self.form_spec), parsed_value)
        ]
        for key_name, dict_element in self.form_spec.elements.items():
            if key_name not in parsed_value:
                if dict_element.required:
                    element_validations.append(
                        shared_type_defs.ValidationMessage(
                            location=[key_name],
                            message=_("Required field missing"),
                            invalid_value=None,
                        )
                    )
                continue

            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            for validation in element_visitor.validate(parsed_value[key_name]):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[key_name] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )

        return element_validations

    def _to_disk(self, raw_value: object, parsed_value: Mapping[str, object]) -> dict[str, object]:
        disk_values = {}
        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in parsed_value
            if is_active:
                disk_values[key_name] = element_visitor.to_disk(parsed_value[key_name])

        for key in self._get_static_elements():
            if key in parsed_value:
                disk_values[key] = parsed_value[key]
        return disk_values
