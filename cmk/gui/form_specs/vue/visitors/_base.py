#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Any, Callable, final, Generic, Sequence, TypeVar

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.vue.visitors._type_defs import (
    DataForDisk,
    DataOrigin,
    FrontendModel,
    InvalidValue,
    ParsedValueModel,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.visitors._type_defs import DefaultValue as FormSpecDefaultValue
from cmk.gui.form_specs.vue.visitors._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
)

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing import vue_formspec_components as shared_type_defs

FormSpecModel = TypeVar("FormSpecModel", bound=FormSpec[Any])


class FormSpecVisitor(abc.ABC, Generic[FormSpecModel, ParsedValueModel, FrontendModel]):
    @final
    def __init__(self, form_spec: FormSpecModel, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    @final
    def to_vue(self, raw_value: object) -> tuple[shared_type_defs.FormSpec, object]:
        parsed_value = self._parse_value(self._migrate_disk_value(raw_value))
        return self._to_vue(raw_value, parsed_value)

    @final
    def validate(self, raw_value: object) -> list[shared_type_defs.ValidationMessage]:
        parsed_value = self._parse_value(self._migrate_disk_value(raw_value))
        # Stage 1: Check if the value is invalid
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(parsed_value.fallback_value, parsed_value.reason)

        # Stage 2: Check if the value of the nested elements report problems
        if nested_validations := self._validate(raw_value, parsed_value):
            # NOTE: During the migration phase, the Stage1 errors from
            #       non-migrated visitors may appear here -> OK
            return nested_validations

        # Stage 3: Execute validators of the element itself
        return compute_validation_errors(
            self._validators(), parsed_value, self._to_disk(raw_value, parsed_value)
        )

    @final
    def to_disk(self, raw_value: object) -> DataForDisk:
        parsed_value = self._parse_value(self._migrate_disk_value(raw_value))
        if isinstance(parsed_value, InvalidValue):
            raise MKGeneralException(
                "Unable to serialize invalid value. Reason: %s" % parsed_value.reason
            )
        return self._to_disk(raw_value, parsed_value)

    def _migrate_disk_value(self, value: object) -> object:
        if (
            not isinstance(value, FormSpecDefaultValue)
            and self.options.data_origin == DataOrigin.DISK
            and self.form_spec.migrate
        ):
            return self.form_spec.migrate(value)
        return value

    @abc.abstractmethod
    def _parse_value(self, raw_value: object) -> ParsedValueModel | InvalidValue[FrontendModel]:
        """Handle the raw value from the form and return a parsed value.

        E.g., replaces DefaultValue sentinel with the actual default value
        or returns EmptyValue if the raw value is of invalid data type."""

    @abc.abstractmethod
    def _to_vue(
        self, raw_value: object, parsed_value: ParsedValueModel | InvalidValue[FrontendModel]
    ) -> tuple[shared_type_defs.FormSpec, FrontendModel]:
        """Returns frontend representation of the FormSpec schema and its data value."""

    def _validators(self) -> Sequence[Callable[[DataForDisk], object]]:
        return compute_validators(self.form_spec)

    def _validate(
        self, raw_value: object, parsed_value: ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        """Validates the nested values of this form spec"""
        return []

    @abc.abstractmethod
    def _to_disk(self, raw_value: object, parsed_value: ParsedValueModel) -> DataForDisk:
        """Transforms the value into a serializable format for disk storage."""
