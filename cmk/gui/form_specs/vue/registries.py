#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Any, Callable, final, Generic, TypeVar

from cmk.gui.form_specs.private import UnknownFormSpec
from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.form_specs.vue.type_defs import DataForDisk, EmptyValue, Value, VisitorOptions
from cmk.gui.utils.rule_specs.loader import LoadedRuleSpec

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

form_spec_registry: dict[str, LoadedRuleSpec] = {}

FormSpecModel = TypeVar("FormSpecModel", bound=FormSpec[Any])


class FormSpecVisitor(abc.ABC, Generic[FormSpecModel, ModelT]):
    @final
    def __init__(self, form_spec: FormSpecModel, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

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
        parsed_value = self._parse_value(raw_value)
        if isinstance(parsed_value, EmptyValue):
            raise MKGeneralException("Unable to serialize empty value")
        return self._to_disk(raw_value, parsed_value)

    @abc.abstractmethod
    def _to_vue(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> tuple[VueComponents.FormSpec, Value]: ...

    @abc.abstractmethod
    def _validate(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> list[VueComponents.ValidationMessage]: ...

    @abc.abstractmethod
    def _to_disk(self, raw_value: object, parsed_value: ModelT) -> DataForDisk: ...


# TODO: why is the registry dict defined here, but the function to put and get from that dict in utils?
# maybe we could bundle this into visitors?

RecomposerFunction = Callable[[FormSpec[Any]], FormSpec[Any]]
form_specs_visitor_registry: dict[
    type[FormSpec[Any]], tuple[type[FormSpecVisitor[FormSpec[Any], Any]], RecomposerFunction | None]
] = {}


def register_visitor_class(
    form_spec_class: type[FormSpec[ModelT]],
    visitor_class: type[FormSpecVisitor[Any, ModelT]],
    recomposer: RecomposerFunction | None = None,
) -> None:
    form_specs_visitor_registry[form_spec_class] = (visitor_class, recomposer)


def get_visitor(
    form_spec: FormSpec[ModelT], options: VisitorOptions
) -> FormSpecVisitor[FormSpec[ModelT], ModelT]:
    if registered_form_spec := form_specs_visitor_registry.get(form_spec.__class__):
        visitor, recomposer_function = registered_form_spec
        if recomposer_function is not None:
            form_spec = recomposer_function(form_spec)
            return get_visitor(form_spec, options)
        return visitor(form_spec, options)

    # If the form spec has no valid visitor, convert it to the legacy valuespec visitor
    visitor, unknown_decomposer = form_specs_visitor_registry[UnknownFormSpec]
    assert unknown_decomposer is not None
    return visitor(unknown_decomposer(form_spec), options)
