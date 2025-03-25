#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import assert_never, TypedDict

from cmk.gui.form_specs.private.multiple_choice import (
    MultipleChoiceExtended,
    MultipleChoiceExtendedLayout,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.form_specs.vue.visitors._base import FormSpecVisitor
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin, DefaultValue, InvalidValue
from cmk.gui.form_specs.vue.visitors._utils import (
    compute_validators,
    get_prefill_default,
    get_title_and_help,
)
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.valuespec import autocompleter_registry

from cmk.shared_typing import vue_formspec_components as shared_type_defs


class TransportFormat(TypedDict):
    """We to transport the title to the frontend to display the selected options both in
    FormReadOnly and FormEdit, because we cannot query the autocompleter there."""

    name: str
    title: str


_ParsedValueModel = Sequence[TransportFormat]
_FrontendModel = Sequence[TransportFormat]


class MultipleChoiceVisitor(
    FormSpecVisitor[MultipleChoiceExtended, _ParsedValueModel, _FrontendModel]
):
    def _get_elements(self) -> _FrontendModel:
        if isinstance(self.form_spec.elements, shared_type_defs.Autocompleter):
            autocompleter_ident = self.form_spec.elements.data.ident
            autocompleter_fn = autocompleter_registry[autocompleter_ident]
            return [
                {"name": name, "title": title} for name, title in autocompleter_fn("", {}) if name
            ]
        return [
            {"name": element.name, "title": element.title.localize(translate_to_current_language)}
            for element in self.form_spec.elements
        ]

    def _get_valid_choices(self) -> set[str]:
        return {element["name"] for element in self._get_elements()}

    def _filter_out_invalid_choices(
        self, raw_value: Sequence[TransportFormat]
    ) -> _ParsedValueModel:
        valid_raw_value_names = set([v["name"] for v in raw_value]) & self._get_valid_choices()
        return [v for v in raw_value if v["name"] in valid_raw_value_names]

    def _build_data_format_from_names(self, names: Sequence[str]) -> _ParsedValueModel:
        return [element for element in self._get_elements() if element["name"] in names]

    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if isinstance(raw_value, DefaultValue):
            fallback_value: _FrontendModel = []
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill, fallback_value),
                InvalidValue,
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, list):
            return InvalidValue(reason=_("Invalid data"), fallback_value=[])

        match self.options.data_origin:
            case DataOrigin.DISK:
                return sorted(
                    self._build_data_format_from_names(raw_value), key=lambda v: v["name"]
                )
            case DataOrigin.FRONTEND:
                # Filter out invalid choices without warning
                return sorted(self._filter_out_invalid_choices(raw_value), key=lambda v: v["name"])
            case other:
                assert_never(other)

    def _to_vue(
        self, raw_value: object, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[
        shared_type_defs.DualListChoice | shared_type_defs.CheckboxListChoice, _FrontendModel
    ]:
        title, help_text = get_title_and_help(self.form_spec)

        if isinstance(self.form_spec.elements, shared_type_defs.Autocompleter):
            elements = []
        else:
            elements = [
                shared_type_defs.MultipleChoiceElement(
                    name=element.name,
                    title=element.title.localize(translate_to_current_language),
                )
                for element in self.form_spec.elements
            ]

        if self.form_spec.layout.value == MultipleChoiceExtendedLayout.dual_list or (
            self.form_spec.layout.value == MultipleChoiceExtendedLayout.auto and len(elements) > 15
        ):
            return (
                shared_type_defs.DualListChoice(
                    title=title,
                    help=help_text,
                    elements=elements,
                    validators=build_vue_validators(compute_validators(self.form_spec)),
                    autocompleter=self.form_spec.elements
                    if isinstance(self.form_spec.elements, shared_type_defs.Autocompleter)
                    else None,
                    i18n=self._get_i18n(),
                    show_toggle_all=self.form_spec.show_toggle_all,
                ),
                parsed_value.fallback_value
                if isinstance(parsed_value, InvalidValue)
                else parsed_value,
            )
        # checkbox list or auto with <= 15 elements
        return (
            shared_type_defs.CheckboxListChoice(
                title=title,
                help=help_text,
                elements=elements,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                i18n=self._get_i18n(),
            ),
            [] if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    def _get_i18n(self) -> shared_type_defs.DualListChoiceI18n:
        return shared_type_defs.DualListChoiceI18n(
            add_all=_("Add all >>"),
            remove_all=_("<< Remove all"),
            add=_("Add >"),
            remove=_("< Remove"),
            available_options=_("Available options"),
            selected_options=_("Selected options"),
            search_available_options=_("Search available options"),
            search_selected_options=_("Search selected options"),
            selected=_("Selected"),
            no_elements_available=_("No elements available"),
            no_elements_selected=_("No elements selected"),
            autocompleter_loading=_("Loading"),
            and_x_more=_("and %s more"),
        )

    def _to_disk(self, parsed_value: _ParsedValueModel) -> list[str]:
        return [v["name"] for v in parsed_value]
