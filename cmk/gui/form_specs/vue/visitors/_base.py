#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Any, final, Generic, TypeVar

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.visitors._type_defs import DataForDisk, DataOrigin
from cmk.gui.form_specs.vue.visitors._type_defs import DefaultValue as FormSpecDefaultValue
from cmk.gui.form_specs.vue.visitors._type_defs import EmptyValue, Value, VisitorOptions

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

FormSpecModel = TypeVar("FormSpecModel", bound=FormSpec[Any])


class FormSpecVisitor(abc.ABC, Generic[FormSpecModel, ModelT]):
    @final
    def __init__(self, form_spec: FormSpecModel, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    @final
    def to_vue(self, raw_value: object) -> tuple[shared_type_defs.FormSpec, Value]:
        parsed_value = self._parse_value(self._migrate_disk_value(raw_value))
        return self._to_vue(raw_value, parsed_value)

    @final
    def validate(self, raw_value: object) -> list[shared_type_defs.ValidationMessage]:
        parsed_value = self._parse_value(self._migrate_disk_value(raw_value))
        return self._validate(raw_value, parsed_value)

    @final
    def to_disk(self, raw_value: object) -> DataForDisk:
        parsed_value = self._parse_value(self._migrate_disk_value(raw_value))
        if isinstance(parsed_value, EmptyValue):
            raise MKGeneralException("Unable to serialize empty value")
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
    def _parse_value(self, raw_value: object) -> ModelT | EmptyValue:
        """Handle the raw value from the form and return a parsed value.

        E.g., replaces DefaultValue sentinel with the actual default value
        or returns EmptyValue if the raw value is of invalid data type."""

    @abc.abstractmethod
    def _to_vue(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> tuple[shared_type_defs.FormSpec, Value]:
        """Returns frontend representation of the FormSpec schema and its data value."""

    @abc.abstractmethod
    def _validate(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        """Validates the parsed value and returns a list of validation error messages."""

    @abc.abstractmethod
    def _to_disk(self, raw_value: object, parsed_value: ModelT) -> DataForDisk:
        """Transforms the value into a serializable format for disk storage."""
