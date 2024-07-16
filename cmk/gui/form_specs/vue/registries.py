#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Callable, final, Generic

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.type_defs import DataForDisk, EmptyValue, Value, VisitorOptions
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

form_spec_registry: dict[str, LoadedRuleSpec] = {}


class FormSpecVisitor(abc.ABC, Generic[ModelT]):
    @abc.abstractmethod
    def __init__(self, form_spec: FormSpec[ModelT], options: VisitorOptions) -> None: ...

    @abc.abstractmethod
    def _parse_value(self, raw_value: object) -> ModelT | EmptyValue: ...

    @final
    def to_vue(self, raw_value: object) -> tuple[VueComponents.FormSpec, Value]:
        return self._to_vue(raw_value, self._parse_value(raw_value))

    @final
    def validate(self, raw_value: object) -> list[VueComponents.ValidationMessage]:
        return self._validate(raw_value, self._parse_value(raw_value))

    @final
    def to_disk(self, raw_value: object) -> DataForDisk:
        return self._to_disk(raw_value, self._parse_value(raw_value))

    @abc.abstractmethod
    def _to_vue(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> tuple[VueComponents.FormSpec, Value]: ...

    @abc.abstractmethod
    def _validate(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> list[VueComponents.ValidationMessage]: ...

    @abc.abstractmethod
    def _to_disk(self, raw_value: object, parsed_value: ModelT | EmptyValue) -> DataForDisk: ...


form_specs_visitor_registry: dict[type, type[FormSpecVisitor]] = {}
RecomposerFunction = Callable[[FormSpec], FormSpec]
form_specs_recomposer_registry: dict[type, RecomposerFunction] = {}
