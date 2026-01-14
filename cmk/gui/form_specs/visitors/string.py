#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="unreachable"

from typing import override

from cmk.gui.form_specs.unstable import StringAutocompleter
from cmk.gui.i18n import _
from cmk.rulesets.v1.form_specs import FieldSize
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, IncomingData, InvalidValue, RawFrontendData
from ._utils import (
    compute_input_hint,
    compute_label,
    get_prefill_default,
    get_title_and_help_with_optional_macro_support,
)
from .validators import build_vue_validators

_ParsedValueModel = str
_FallbackModel = str


class StringVisitor(FormSpecVisitor[StringAutocompleter, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            fallback_value: _FallbackModel = ""
            if isinstance(
                prefill_default := get_prefill_default(
                    self.form_spec.prefill, fallback_value=fallback_value
                ),
                InvalidValue,
            ):
                return prefill_default
            raw_value = RawFrontendData(prefill_default)

        if not isinstance(raw_value.value, str):
            return InvalidValue(reason=_("Invalid string"), fallback_value="")

        return raw_value.value

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.FormSpec, object]:
        title, help_text = get_title_and_help_with_optional_macro_support(
            self.form_spec, self.form_spec.macro_support
        )
        return (
            shared_type_defs.String(
                title=title,
                help=help_text,
                label=compute_label(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=compute_input_hint(self.form_spec.prefill),
                field_size=field_size_translator(self.form_spec.field_size),
                autocompleter=self.form_spec.autocompleter,
            ),
            (
                parsed_value.fallback_value
                if isinstance(parsed_value, InvalidValue)
                else parsed_value
            ),
        )

    @override
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
