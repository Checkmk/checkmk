#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc.i18n import _
from cmk.rulesets.v1.form_specs import MultilineText
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, IncomingData, InvalidValue
from ._utils import (
    compute_input_hint,
    compute_label,
    get_prefill_default,
    get_title_and_help_with_optional_macro_support,
)
from .validators import build_vue_validators

_ParsedValueModel = str
_FallbackModel = str


class MultilineTextVisitor(FormSpecVisitor[MultilineText, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill, ""), InvalidValue
            ):
                return prefill_default
            value: object = prefill_default
        else:
            value = raw_value.value

        if not isinstance(value, str):
            return InvalidValue(reason=_("Invalid text"), fallback_value="")
        return value

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.FormSpec, object]:
        title, help_text = get_title_and_help_with_optional_macro_support(
            self.form_spec, self.form_spec.macro_support
        )
        return (
            shared_type_defs.MultilineText(
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                input_hint=compute_input_hint(self.form_spec.prefill),
                monospaced=self.form_spec.monospaced,
                macro_support=self.form_spec.macro_support,
                label=compute_label(self.form_spec.label),
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> str:
        return parsed_value
