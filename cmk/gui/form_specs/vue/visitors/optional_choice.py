#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Never, override

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private.optional_choice import OptionalChoice

from cmk.rulesets.v1 import Label
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._registry import get_visitor
from .._type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    IncomingData,
    InvalidValue,
    RawDiskData,
    RawFrontendData,
)
from .._utils import (
    compute_validators,
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

_ParsedValueModel = RawDiskData | RawFrontendData
_FallbackModel = Never


class OptionalChoiceVisitor(FormSpecVisitor[OptionalChoice, _ParsedValueModel, _FallbackModel]):
    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        # Note: the raw_value None is reserved for the optional choice checkbox
        if isinstance(raw_value, DefaultValue):
            return RawDiskData(None)
        return raw_value

    def _compute_label(self) -> str:
        if self.form_spec.label is not None:
            return localize(self.form_spec.label)
        title = localize(self.form_spec.title)
        if title:
            return title
        return localize(Label(" Activate this option"))

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.OptionalChoice, object]:
        title, help_text = get_title_and_help(self.form_spec)

        if isinstance(parsed_value, InvalidValue):
            parsed_value = RawDiskData(None)

        visitor = get_visitor(self.form_spec.parameter_form)
        embedded_schema, embedded_value = visitor.to_vue(
            parsed_value if parsed_value.value is not None else DEFAULT_VALUE
        )
        if embedded_value is None:
            raise MKGeneralException(
                "Unable to configure OptionalChoice with None as embedded value"
            )

        return (
            shared_type_defs.OptionalChoice(
                title=title,
                help=help_text,
                i18n=shared_type_defs.I18nOptionalChoice(
                    label=self._compute_label(),
                    none_label=localize(self.form_spec.none_label),
                ),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                parameter_form=embedded_schema,
                parameter_form_default_value=embedded_value,
            ),
            None if parsed_value.value is None else embedded_value,
        )

    @override
    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        validation_errors: list[shared_type_defs.ValidationMessage] = []
        if parsed_value.value is not None:
            for validation_error in get_visitor(self.form_spec.parameter_form).validate(
                parsed_value
            ):
                validation_errors.append(
                    shared_type_defs.ValidationMessage(
                        location=["parameter_form"],
                        message=validation_error.message,
                        replacement_value=validation_error.replacement_value,
                    )
                )

        return validation_errors

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> object:
        if parsed_value.value is None:
            return None
        return get_visitor(self.form_spec.parameter_form).to_disk(parsed_value)
