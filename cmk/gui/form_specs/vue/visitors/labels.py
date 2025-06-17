#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.form_specs.private.labels import Labels
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _, translate_to_current_language

from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import InvalidValue
from ._utils import get_title_and_help

_ParsedValueModel = Mapping[str, str]
_FrontendModel = Mapping[str, str]


class LabelsVisitor(FormSpecVisitor[Labels, _ParsedValueModel, _FrontendModel]):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if not isinstance(raw_value, dict):
            return InvalidValue(reason=_("Invalid data"), fallback_value={})

        for value in raw_value.values():
            if not isinstance(value, str):
                return InvalidValue(reason=_("Invalid data"), fallback_value={})

        return raw_value

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.Labels, Mapping[str, str]]:
        title, help_text = get_title_and_help(self.form_spec)

        return (
            shared_type_defs.Labels(
                title=title,
                help=help_text,
                i18n=shared_type_defs.LabelsI18n(
                    remove_label=translate_to_current_language("Remove label"),
                    add_some_labels=translate_to_current_language("Add some labels"),
                    key_value_format_error=translate_to_current_language(
                        "Labels need to be in the format [KEY]:[VALUE]. For example os:windows."
                    ),
                    max_labels_reached=translate_to_current_language("Max labels reached"),
                    uniqueness_error=translate_to_current_language("Labels need to be unique."),
                ),
                validators=build_vue_validators(self._validators()),
                autocompleter=shared_type_defs.Autocompleter(
                    data=shared_type_defs.AutocompleterData(
                        ident="label",
                        params=shared_type_defs.AutocompleterParams(
                            world=self.form_spec.world.value
                        ),
                    ),
                ),
                max_labels=self.form_spec.max_labels,
                label_source=(
                    self.form_spec.label_source.value if self.form_spec.label_source else None
                ),
            ),
            (
                parsed_value.fallback_value
                if isinstance(parsed_value, InvalidValue)
                else parsed_value
            ),
        )

    def _to_disk(self, parsed_value: _ParsedValueModel) -> Mapping[str, str]:
        return parsed_value
