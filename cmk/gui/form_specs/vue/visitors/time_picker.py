#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Literal, override

from cmk.ccc.i18n import _
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ...unstable import TimePicker
from .._type_defs import DefaultValue, IncomingData, InvalidValue
from .._utils import (
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

type _ParsedValueModel = str
type _FallbackModel = str | Literal[""]


class TimePickerVisitor(FormSpecVisitor[TimePicker, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue) or not isinstance(raw_value.value, str):
            return InvalidValue(reason=_("Invalid time format"), fallback_value="")
        try:
            time.strptime(raw_value.value, "%H:%M")
        except (ValueError, TypeError):
            return InvalidValue(
                reason=_("Invalid time format %s") % raw_value.value, fallback_value=""
            )

        return raw_value.value

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.TimePicker, object]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.TimePicker(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> str:
        return parsed_value
