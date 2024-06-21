#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Any, Callable, Generic

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.type_defs import DataForDisk, ModelT, Value, VisitorOptions
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.rulesets.v1.form_specs import FormSpec

form_spec_registry: dict[str, LoadedRuleSpec] = {}


class FormSpecVisitor(abc.ABC, Generic[ModelT]):
    @abc.abstractmethod
    def __init__(self, form_spec: FormSpec[ModelT], options: VisitorOptions) -> None: ...

    @abc.abstractmethod
    def parse_value(self, value: Any) -> ModelT: ...

    @abc.abstractmethod
    def to_vue(self, value: ModelT) -> tuple[VueComponents.FormSpec, Value]: ...

    @abc.abstractmethod
    def validate(self, value: ModelT) -> list[VueComponents.ValidationMessage]: ...

    @abc.abstractmethod
    def to_disk(self, value: ModelT) -> DataForDisk: ...


form_specs_visitor_registry: dict[type, type[FormSpecVisitor]] = {}
RecomposerFunction = Callable[[FormSpec], FormSpec]
form_specs_recomposer_registry: dict[type, RecomposerFunction] = {}
