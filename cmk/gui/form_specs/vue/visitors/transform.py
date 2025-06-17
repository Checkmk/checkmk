#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.i18n import _

from cmk.shared_typing import vue_formspec_components as VueComponents

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DataOrigin, InvalidValue

_ParsedValueModel = object
_FrontendModel = object


class TransformVisitor(
    FormSpecVisitor[
        TransformDataForLegacyFormatOrRecomposeFunction,
        _ParsedValueModel,
        _FrontendModel,
    ]
):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if self.options.data_origin == DataOrigin.FRONTEND:
            return raw_value
        try:
            return self.form_spec.from_disk(raw_value)
        except ValueError:
            return InvalidValue(reason=_("Unable to transform value"), fallback_value=raw_value)

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[VueComponents.FormSpec, object]:
        return get_visitor(self.form_spec.wrapped_form_spec, self.options).to_vue(parsed_value)

    def _validate(self, parsed_value: _ParsedValueModel) -> list[VueComponents.ValidationMessage]:
        return get_visitor(self.form_spec.wrapped_form_spec, self.options).validate(parsed_value)

    def _to_disk(self, parsed_value: _ParsedValueModel) -> object:
        return self.form_spec.to_disk(
            get_visitor(self.form_spec.wrapped_form_spec, self.options).to_disk(parsed_value)
        )
