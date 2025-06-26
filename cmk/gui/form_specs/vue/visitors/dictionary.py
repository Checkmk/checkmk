#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
from collections.abc import Mapping, Sequence
from typing import cast

from cmk.gui.form_specs.private.dictionary_extended import DictGroupExtended, DictionaryExtended
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _

from cmk.rulesets.v1.form_specs._composed import NoGroup
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.vue_formspec_components import DictionaryGroupLayout

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DataOrigin, DEFAULT_VALUE, DefaultValue, InvalidValue
from ._utils import (
    base_i18n_form_spec,
    compute_validators,
    get_title_and_help,
    localize,
)

_ParsedValueModel = Mapping[str, object]
_FrontendModel = Mapping[str, object]


class DictionaryVisitor(FormSpecVisitor[DictionaryExtended, _ParsedValueModel, _FrontendModel]):
    def _compute_default_values(self) -> _ParsedValueModel:
        default_values = {
            k: DEFAULT_VALUE for k, el in self.form_spec.elements.items() if el.required
        }
        if self.form_spec.default_checked is not None:
            default_values.update({k: DEFAULT_VALUE for k in self.form_spec.default_checked})
        return default_values

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

    def _get_invalid_keys(self, value: dict[str, object]) -> Sequence[str]:
        valid_keys = self.form_spec.elements.keys()
        return list(value.keys() - valid_keys - self._get_static_elements())

    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        raw_value = (
            self._compute_default_values() if isinstance(raw_value, DefaultValue) else raw_value
        )
        if not isinstance(raw_value, Mapping):
            return InvalidValue[_FrontendModel](
                reason=_("Invalid datatype of value: %s") % type(raw_value),
                fallback_value=cast(_FrontendModel, self.to_vue(DEFAULT_VALUE)[1]),
            )

        try:
            resolved_dict = self._resolve_static_elements(raw_value)
            if invalid_keys := self._get_invalid_keys(resolved_dict):
                return InvalidValue[_FrontendModel](
                    reason=_("Dictionary contains invalid keys: %r") % invalid_keys,
                    fallback_value=cast(_FrontendModel, self.to_vue(DEFAULT_VALUE)[1]),
                )
            return resolved_dict
        except ValueError as e:
            # This can happen during parsing the static elements with ast.literal_eval
            return InvalidValue[_FrontendModel](
                reason=_("General value error: %s") % e,
                fallback_value=cast(_FrontendModel, self.to_vue(DEFAULT_VALUE)[1]),
            )

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.Dictionary, _FrontendModel]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, InvalidValue):
            parsed_value = parsed_value.fallback_value

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
                layout = (
                    dict_element.group.layout
                    if isinstance(dict_element.group, DictGroupExtended)
                    else DictionaryGroupLayout.horizontal
                )
                group = shared_type_defs.DictionaryGroup(
                    title=localize(dict_element.group.title),
                    help=localize(dict_element.group.help_text),
                    key=repr(dict_element.group.title) + repr(dict_element.group.help_text),
                    layout=layout,
                )

            if is_active or dict_element.required:
                vue_values[key_name] = element_vue_value

            elements_keyspec.append(
                shared_type_defs.DictionaryElement(
                    name=key_name,
                    default_value=element_vue_value,
                    required=dict_element.required,
                    parameter_form=element_schema,
                    render_only=dict_element.render_only,
                    group=group,
                )
            )

        return (
            shared_type_defs.Dictionary(
                groups=[],
                title=title,
                help=help_text,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                elements=elements_keyspec,
                no_elements_text=localize(self.form_spec.no_elements_text),
                additional_static_elements=self._compute_static_elements(parsed_value),
                i18n_base=base_i18n_form_spec(),
            ),
            vue_values,
        )

    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        # NOTE: the parsed_value may include keys with default values, e.g. {"ce": default_value}
        element_validations = []
        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)

            if key_name not in parsed_value:
                if dict_element.required:
                    element_validations.append(
                        shared_type_defs.ValidationMessage(
                            location=[key_name],
                            message=_("Required field missing"),
                            replacement_value=element_visitor.to_vue(DEFAULT_VALUE)[1],
                        )
                    )
                continue

            for validation in element_visitor.validate(parsed_value[key_name]):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[key_name] + validation.location,
                        message=validation.message,
                        replacement_value=validation.replacement_value,
                    )
                )

        return element_validations

    def _to_disk(self, parsed_value: _ParsedValueModel) -> dict[str, object]:
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
