#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.vue._base import FormSpecVisitor
from cmk.gui.i18n import _

from cmk.shared_typing import vue_formspec_components as VueComponents

from .._registry import get_visitor
from .._type_defs import IncomingData, InvalidValue, RawDiskData

_ParsedValueModel = IncomingData
_FallbackModel = object


class TransformVisitor(
    FormSpecVisitor[
        TransformDataForLegacyFormatOrRecomposeFunction,
        _ParsedValueModel,
        _FallbackModel,
    ]
):
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, RawDiskData):
            try:
                return RawDiskData(self.form_spec.from_disk(raw_value.value))
            except ValueError:
                return InvalidValue(
                    reason=_("Unable to transform value"), fallback_value=raw_value.value
                )

        return raw_value

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[VueComponents.FormSpec, object]:
        value = (
            RawDiskData(parsed_value.fallback_value)
            if isinstance(parsed_value, InvalidValue)
            else parsed_value
        )
        return get_visitor(self.form_spec.wrapped_form_spec).to_vue(value)

    def _validate(self, parsed_value: _ParsedValueModel) -> list[VueComponents.ValidationMessage]:
        return get_visitor(self.form_spec.wrapped_form_spec).validate(parsed_value)

    def _to_disk(self, parsed_value: _ParsedValueModel) -> object:
        return self.form_spec.to_disk(
            get_visitor(self.form_spec.wrapped_form_spec).to_disk(parsed_value)
        )
