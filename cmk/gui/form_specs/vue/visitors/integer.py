#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import Literal, override

from cmk.ccc.i18n import _
from cmk.gui.form_specs.private.validators import IsInteger
from cmk.rulesets.v1.form_specs import Integer
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._type_defs import DefaultValue, IncomingData, InvalidValue
from .._utils import (
    compute_input_hint,
    compute_validators,
    get_prefill_default,
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

_ParsedValueModel = int
_FallbackModel = int | Literal[""]


class IntegerVisitor(FormSpecVisitor[Integer, _ParsedValueModel, _FallbackModel]):
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
            value: object = prefill_default
        else:
            value = raw_value.value

        #  23 / -23 / "23" / "-23" -> OK
        #  23.0 / "23.0" / other   -> INVALID
        if not isinstance(value, int):
            return InvalidValue[_FallbackModel](
                reason=_("Not an integer number"), fallback_value=""
            )

        try:
            return int(value)
        except ValueError:
            return InvalidValue[_FallbackModel](
                reason=_("Not an integer number"), fallback_value=""
            )

    @override
    def _validators(self) -> Sequence[Callable[[int], object]]:
        return [IsInteger()] + compute_validators(self.form_spec)

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
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
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> int:
        return parsed_value
