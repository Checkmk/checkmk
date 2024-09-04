#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private.optional_choice import OptionalChoice
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Label, Title

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EmptyValue
from ._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_title_and_help,
    localize,
)


class OptionalChoiceVisitor(FormSpecVisitor[OptionalChoice, object]):
    def _parse_value(self, raw_value: object) -> object | EmptyValue:
        # Note: the raw_value None is reserved for the optional choice checkbox
        if isinstance(raw_value, DefaultValue):
            return None
        return raw_value

    def _compute_label(self):
        if self.form_spec.label is not None:
            return localize(self.form_spec.label)
        title = localize(self.form_spec.title)
        if title:
            return title
        return localize(Label(" Activate this option"))

    def _to_vue(
        self, raw_value: object, parsed_value: object | EmptyValue
    ) -> tuple[shared_type_defs.OptionalChoice, object]:
        title, help_text = get_title_and_help(self.form_spec)

        visitor = get_visitor(self.form_spec.parameter_form, self.options)
        embedded_schema, embedded_value = visitor.to_vue(
            parsed_value if parsed_value is not None else DEFAULT_VALUE
        )
        if embedded_value is None:
            raise MKGeneralException(
                "Unable to configure OptionalChoice with None as embedded value"
            )
        if isinstance(parsed_value, EmptyValue):
            parsed_value = None

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
            None if parsed_value is None else embedded_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: object | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            # Do not display the optional choice value
            # It might include sensitive data from the wrapped form spec
            return create_validation_error(
                None,
                Title("Invalid optional choice"),
            )
        validation_errors = compute_validation_errors(
            compute_validators(self.form_spec), parsed_value
        )
        if parsed_value is not None:
            for validation_error in get_visitor(
                self.form_spec.parameter_form, self.options
            ).validate(parsed_value):
                validation_errors.append(
                    shared_type_defs.ValidationMessage(
                        location=["parameter_form"],
                        message=validation_error.message,
                        invalid_value=validation_error.invalid_value,
                    )
                )

        return validation_errors

    def _to_disk(self, raw_value: object, parsed_value: object) -> object:
        if parsed_value is None:
            return parsed_value
        return get_visitor(self.form_spec.parameter_form, self.options).to_disk(parsed_value)
