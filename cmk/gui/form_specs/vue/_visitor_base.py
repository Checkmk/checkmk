#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from collections.abc import Callable, Sequence
from typing import Any, final, Generic, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._type_defs import DiskModel, IncomingData, InvalidValue, RawDiskData, VisitorOptions
from ._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
)

FormSpecModel = TypeVar("FormSpecModel", bound=FormSpec[Any])

_ParsedValueModel = TypeVar("_ParsedValueModel")
_FallbackDataModel = TypeVar("_FallbackDataModel")


class FormSpecVisitor(abc.ABC, Generic[FormSpecModel, _ParsedValueModel, _FallbackDataModel]):
    @final
    def __init__(self, form_spec: FormSpecModel, visitor_options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.visitor_options = visitor_options

    @final
    def to_vue(self, raw_value: IncomingData) -> tuple[shared_type_defs.FormSpec, object]:
        parsed_value = self._parse_value(
            self._migrate_disk_value(raw_value)
            if self.visitor_options.migrate_values
            else raw_value
        )
        return self._to_vue(parsed_value)

    @final
    def validate(self, raw_value: IncomingData) -> list[shared_type_defs.ValidationMessage]:
        parsed_value = self._parse_value(
            self._migrate_disk_value(raw_value)
            if self.visitor_options.migrate_values
            else raw_value
        )
        # Stage 1: Check if the value is invalid
        if isinstance(parsed_value, InvalidValue):
            return create_validation_error(self._to_vue(parsed_value)[1], parsed_value.reason)

        # Stage 2: Check if the value of the nested elements report problems
        if nested_validations := self._validate(parsed_value):
            # NOTE: During the migration phase, the Stage1 errors from
            #       non-migrated visitors may appear here -> OK
            return nested_validations

        # Stage 3: Execute validators of the element itself
        return compute_validation_errors(
            self._validators(),
            lambda: self._to_vue(parsed_value)[1],
            self._to_disk(parsed_value),
        )

    @final
    def to_disk(self, raw_value: IncomingData) -> DiskModel:
        parsed_value = self._parse_value(
            self._migrate_disk_value(raw_value)
            if self.visitor_options.migrate_values
            else raw_value
        )
        if isinstance(parsed_value, InvalidValue):
            raise MKGeneralException(
                "Unable to serialize invalid value. Reason: %s" % parsed_value.reason
            )
        return self._to_disk(parsed_value)

    def _migrate_disk_value(self, value: IncomingData) -> IncomingData:
        if isinstance(value, RawDiskData) and self.form_spec.migrate:
            return RawDiskData(value=self.form_spec.migrate(value.value))
        return value

    @abc.abstractmethod
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackDataModel]:
        """Handle the raw value from the form and return a parsed value.

        E.g., replaces DefaultValue sentinel with the actual default value
        or returns EmptyValue if the raw value is of invalid data type."""

    @abc.abstractmethod
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackDataModel]
    ) -> tuple[shared_type_defs.FormSpec, object]:
        """Returns frontend representation of the FormSpec schema and its data value."""

    def _validators(self) -> Sequence[Callable[[DiskModel], object]]:
        return compute_validators(self.form_spec)

    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        """Validates the nested values of this form spec"""
        return []

    @abc.abstractmethod
    def _to_disk(self, parsed_value: _ParsedValueModel) -> DiskModel:
        """Transforms the value into a serializable format for disk storage."""
