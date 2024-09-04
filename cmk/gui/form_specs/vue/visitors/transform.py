#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.converter import TransformForLegacyData
from cmk.gui.form_specs.vue import shared_type_defs as VueComponents

from cmk.rulesets.v1 import Message

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DataOrigin, EmptyValue
from ._utils import create_validation_error


class TransformVisitor(FormSpecVisitor[TransformForLegacyData, object]):
    def _parse_value(self, raw_value: object) -> object:
        if self.options.data_origin == DataOrigin.FRONTEND:
            return raw_value
        try:
            return self.form_spec.from_disk(raw_value)
        except ValueError:
            return EmptyValue

    def _to_vue(
        self, raw_value: object, parsed_value: object | EmptyValue
    ) -> tuple[VueComponents.FormSpec, object]:
        return get_visitor(self.form_spec.wrapped_form_spec, self.options).to_vue(parsed_value)

    def _validate(
        self, raw_value: object, parsed_value: object | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if parsed_value is EmptyValue:
            return create_validation_error(raw_value, Message("Unable to transform value"))
        return get_visitor(self.form_spec.wrapped_form_spec, self.options).validate(parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: object) -> object:
        return self.form_spec.to_disk(
            get_visitor(self.form_spec.wrapped_form_spec, self.options).to_disk(parsed_value)
        )
