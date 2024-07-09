#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
import dataclasses
from typing import Any, Callable, Generic, NewType

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.type_defs import DataForDisk, Value, VisitorOptions
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

form_spec_registry: dict[str, LoadedRuleSpec] = {}
IsInputHint = NewType("IsInputHint", bool)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ValidValue(Generic[ModelT]):
    value: ModelT


@dataclasses.dataclass(frozen=True, kw_only=True)
class InvalidValue:
    invalid_value: str
    error_message: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class InputHintValue(Generic[ModelT]):
    value: ModelT | str


ParsedValue = ValidValue[ModelT] | InputHintValue[ModelT] | InvalidValue
ValidateValue = ValidValue[ModelT] | InvalidValue


class FormSpecVisitor(abc.ABC, Generic[ModelT]):

    @abc.abstractmethod
    def __init__(self, form_spec: FormSpec[ModelT], options: VisitorOptions) -> None: ...

    @abc.abstractmethod
    def parse_value(self, value: Any) -> ParsedValue[ModelT]: ...

    @abc.abstractmethod
    def to_vue(self, parsed_value: ParsedValue[ModelT]) -> tuple[VueComponents.FormSpec, Value]: ...

    @abc.abstractmethod
    def validate(
        self, parsed_value: ValidateValue[ModelT]
    ) -> list[VueComponents.ValidationMessage]: ...

    @abc.abstractmethod
    def to_disk(self, parsed_value: ValidValue[ModelT]) -> DataForDisk: ...


form_specs_visitor_registry: dict[type, type[FormSpecVisitor]] = {}
RecomposerFunction = Callable[[FormSpec], FormSpec]
form_specs_recomposer_registry: dict[type, RecomposerFunction] = {}
