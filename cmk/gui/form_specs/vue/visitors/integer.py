#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import Literal

from cmk.ccc.i18n import _

from cmk.gui.form_specs.private.validators import IsInteger
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1.form_specs import Integer
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, InvalidValue
from ._utils import (
    base_i18n_form_spec,
    compute_input_hint,
    compute_validators,
    get_prefill_default,
    get_title_and_help,
    localize,
)

_ParsedValueModel = int
_FrontendModel = int | Literal[""]


class IntegerVisitor(FormSpecVisitor[Integer, _ParsedValueModel, _FrontendModel]):
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

        #  23 / -23 / "23" / "-23" -> OK
        #  23.0 / "23.0" / other   -> INVALID
        if not isinstance(raw_value, int):
            return InvalidValue[_FrontendModel](
                reason=_("Not an integer number"), fallback_value=""
            )

        try:
            return int(raw_value)
        except ValueError:
            return InvalidValue[_FrontendModel](
                reason=_("Not an integer number"), fallback_value=""
            )

    def _validators(self) -> Sequence[Callable[[int], object]]:
        return [IsInteger()] + compute_validators(self.form_spec)

    def _to_vue(
        self, raw_value: object, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.Integer, Literal[""] | int]:
        title, help_text = get_title_and_help(self.form_spec)
        input_hint = compute_input_hint(self.form_spec.prefill)
        input_hint_str = None if input_hint is None else str(input_hint)
        return (
            shared_type_defs.Integer(
                title=title,
                help=help_text,
                unit=self.form_spec.unit_symbol,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
                input_hint=input_hint_str,
                i18n_base=base_i18n_form_spec(),
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    def _to_disk(self, parsed_value: _ParsedValueModel) -> int:
        return parsed_value
