#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

from cmk.ccc.i18n import _
from cmk.gui.form_specs.unstable import ListOfStrings
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    IncomingData,
    InvalidValue,
    RawDiskData,
)
from ._utils import (
    compute_validators,
    get_title_and_help,
)
from .validators import build_vue_validators

_ParsedValueModel = Sequence[str]
_FallbackModel = Sequence[str]


class ListOfStringsVisitor(FormSpecVisitor[ListOfStrings, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return self.form_spec.prefill.value

        value = raw_value.value

        if not isinstance(value, list):
            return InvalidValue(reason=_("Not a list"), fallback_value=[""])

        for v in value:
            if not isinstance(v, str):
                return InvalidValue(reason=_("List element is not a number"), fallback_value=[""])

        # Filter empty strings
        return [x for x in value if x]

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.ListOfStrings, object]:
        title, help_text = get_title_and_help(self.form_spec)

        element_visitor = get_visitor(self.form_spec.string_spec, self.visitor_options)
        string_spec, string_default_value = element_visitor.to_vue(DEFAULT_VALUE)

        assert isinstance(string_default_value, str)

        return (
            shared_type_defs.ListOfStrings(
                title=title,
                help=help_text,
                validators=build_vue_validators(compute_validators(self.form_spec)),
                string_spec=string_spec,
                string_default_value=string_default_value,
            ),
            parsed_value.fallback_value if isinstance(parsed_value, InvalidValue) else parsed_value,
        )

    @override
    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        element_validations: list[shared_type_defs.ValidationMessage] = []
        element_visitor = get_visitor(self.form_spec.string_spec, self.visitor_options)

        for idx, entry in enumerate(parsed_value):
            for validation in element_visitor.validate(RawDiskData(entry)):
                element_validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[str(idx)] + list(validation.location),
                        message=validation.message,
                        replacement_value=validation.replacement_value,
                    )
                )
        return element_validations

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> Sequence[str]:
        return parsed_value
