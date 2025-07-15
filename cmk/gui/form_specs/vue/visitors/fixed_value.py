#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import TypeVar

from cmk.ccc.exceptions import MKGeneralException

from cmk.rulesets.v1.form_specs import FixedValue
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._type_defs import IncomingData, InvalidValue
from .._utils import (
    compute_validators,
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

_FixedValueT = TypeVar("_FixedValueT", int, float, str, bool, None)
_ParsedValueModel = int | float | str | bool | None
_FallbackModel = int | float | str | bool | None


class FixedValueVisitor(
    FormSpecVisitor[FixedValue[_FixedValueT], _ParsedValueModel, _FallbackModel]
):
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        return self.form_spec.value

    def _validators(self) -> Sequence[Callable[[_FixedValueT], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.FixedValue, object]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.FixedValue(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label) if self.form_spec.label is not None else None,
                value=parsed_value,
                validators=build_vue_validators(compute_validators(self.form_spec)),
            ),
            self.form_spec.value,
        )

    def _to_disk(self, parsed_value: _ParsedValueModel) -> _ParsedValueModel:
        if isinstance(parsed_value, InvalidValue):
            raise MKGeneralException("Unable to serialize empty value")
        return parsed_value
