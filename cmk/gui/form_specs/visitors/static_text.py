#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import override

from cmk.gui.form_specs.unstable.static_text import StaticText
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, IncomingData, InvalidValue
from ._utils import get_title_and_help

_ParsedValueModel = str
_FallbackModel = str


class StaticTextVisitor(FormSpecVisitor[StaticText, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return ""
        if not isinstance(raw_value.value, str):
            # Non-string injection is treated as "nothing to display"; the
            # widget shows the empty fallback rather than failing the form.
            return ""
        return raw_value.value

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.StaticText, object]:
        title, help_text = get_title_and_help(self.form_spec)
        value = (
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value
        )
        return (
            shared_type_defs.StaticText(
                title=title,
                help=help_text,
                validators=[],
                value=value,
                multiline=self.form_spec.multiline,
            ),
            value,
        )

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> str:
        return parsed_value
