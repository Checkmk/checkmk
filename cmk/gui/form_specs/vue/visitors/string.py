#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

from cmk.gui.form_specs.private import StringAutocompleter
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _

from cmk.rulesets.v1.form_specs import FieldSize
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, InvalidValue
from ._utils import (
    base_i18n_form_spec,
    compute_input_hint,
    compute_label,
    get_prefill_default,
    get_title_and_help,
)

_ParsedValueModel = str
_FrontendModel = str


class StringVisitor(FormSpecVisitor[StringAutocompleter, _ParsedValueModel, _FrontendModel]):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if isinstance(raw_value, DefaultValue):
            fallback_value: _FrontendModel = ""
            if isinstance(
                prefill_default := get_prefill_default(
                    self.form_spec.prefill, fallback_value=fallback_value
                ),
                InvalidValue,
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, str):
            return InvalidValue(reason=_("Invalid string"), fallback_value="")
        return raw_value

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.String, _FrontendModel]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.String(
                title=title,
                help=help_text,
                label=compute_label(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=compute_input_hint(self.form_spec.prefill),
                field_size=field_size_translator(self.form_spec.field_size),
                autocompleter=self.form_spec.autocompleter,
                i18n_base=base_i18n_form_spec(),
            ),
            (
                parsed_value.fallback_value
                if isinstance(parsed_value, InvalidValue)
                else parsed_value
            ),
        )

    def _to_disk(self, parsed_value: _ParsedValueModel) -> str:
        return parsed_value


def field_size_translator(field_size: FieldSize) -> shared_type_defs.StringFieldSize:
    match field_size:
        case FieldSize.SMALL:
            return shared_type_defs.StringFieldSize.SMALL
        case FieldSize.MEDIUM:
            return shared_type_defs.StringFieldSize.MEDIUM
        case FieldSize.LARGE:
            return shared_type_defs.StringFieldSize.LARGE
        case _:
            return shared_type_defs.StringFieldSize.MEDIUM
