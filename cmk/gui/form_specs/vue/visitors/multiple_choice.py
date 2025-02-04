#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.form_specs.private.multiple_choice import (
    MultipleChoiceExtended,
    MultipleChoiceExtendedLayout,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.form_specs.vue.visitors._base import FormSpecVisitor
from cmk.gui.form_specs.vue.visitors._type_defs import DefaultValue, InvalidValue
from cmk.gui.form_specs.vue.visitors._utils import (
    compute_validators,
    get_prefill_default,
    get_title_and_help,
)
from cmk.gui.i18n import _, translate_to_current_language

from cmk.shared_typing import vue_formspec_components as shared_type_defs

_ParsedValueModel = Sequence[str]
_FrontendModel = Sequence[str]


class MultipleChoiceVisitor(
    FormSpecVisitor[MultipleChoiceExtended, _ParsedValueModel, _FrontendModel]
):
    def _is_valid_choice(self, value: str) -> bool:
        if isinstance(self.form_spec.elements, shared_type_defs.Autocompleter):
            return True
        return value in [x.name for x in self.form_spec.elements]

    def _strip_invalid_choices(self, raw_value: list[str]) -> list[str]:
        if isinstance(self.form_spec.elements, shared_type_defs.Autocompleter):
            return raw_value
        valid_choices = {x.name for x in self.form_spec.elements}
        return list(set(raw_value) & valid_choices)

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

        # Filter out invalid choices without warning
        return sorted(self._strip_invalid_choices(raw_value))

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
        return list(parsed_value)
