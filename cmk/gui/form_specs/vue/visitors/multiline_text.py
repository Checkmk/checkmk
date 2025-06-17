#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.i18n import _

from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1.form_specs import MultilineText
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, InvalidValue
from ._utils import (
    compute_input_hint,
    compute_label,
    get_prefill_default,
    get_title_and_help,
)

_ParsedValueModel = str
_FrontendModel = str


class MultilineTextVisitor(FormSpecVisitor[MultilineText, _ParsedValueModel, _FrontendModel]):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill, ""), InvalidValue
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, str):
            return InvalidValue(reason=_("Invalid text"), fallback_value="")
        return raw_value

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.MultilineText, _FrontendModel]:
        title, help_text = get_title_and_help(self.form_spec)
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

    def _to_disk(self, parsed_value: _ParsedValueModel) -> str:
        return parsed_value
