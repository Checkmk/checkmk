#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.


from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


@dataclass(kw_only=True)
class IsInteger:
    type: str = "is_integer"
    error_message: Optional[str] = None


@dataclass(kw_only=True)
class IsFloat:
    type: str = "is_float"
    error_message: Optional[str] = None


@dataclass(kw_only=True)
class LengthInRange:
    type: str = "length_in_range"
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    error_message: Optional[str] = None


@dataclass(kw_only=True)
class NumberInRange:
    type: str = "number_in_range"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    error_message: Optional[str] = None


Validator = Union[IsInteger, IsFloat, NumberInRange, LengthInRange]


class StringFieldSize(str, Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


@dataclass(kw_only=True)
class PasswordStoreChoice:
    password_id: str
    name: str


@dataclass(kw_only=True)
class I18nPassword:
    explicit_password: str
    password_store: str
    no_password_store_choices: str
    password_choice_invalid: str


@dataclass(kw_only=True)
class DictionaryGroup:
    key: str
    title: str
    help: Optional[str] = None


class DictionaryLayout(str, Enum):
    one_column = "one_column"
    two_columns = "two_columns"


@dataclass(kw_only=True)
class SingleChoiceElement:
    name: Any
    title: str


@dataclass(kw_only=True)
class MultipleChoiceElement:
    name: str
    title: str


class CascadingChoiceLayout(str, Enum):
    vertical = "vertical"
    horizontal = "horizontal"


@dataclass(kw_only=True)
class TimeSpanI18n:
    millisecond: str
    second: str
    minute: str
    hour: str
    day: str


class TimeSpanTimeMagnitude(str, Enum):
    millisecond = "millisecond"
    second = "second"
    minute = "minute"
    hour = "hour"
    day = "day"


@dataclass(kw_only=True)
class ValidationMessage:
    location: list[str]
    message: str
    invalid_value: Any


@dataclass(kw_only=True)
class FormSpec:
    type: str
    title: str
    help: str
    validators: list[Validator] = field(default_factory=lambda: [])


@dataclass(kw_only=True)
class Integer(FormSpec):
    type: str = "integer"
    label: Optional[str] = None
    unit: Optional[str] = None
    input_hint: Optional[str] = None


@dataclass(kw_only=True)
class Float(FormSpec):
    type: str = "float"
    label: Optional[str] = None
    unit: Optional[str] = None
    input_hint: Optional[str] = None


@dataclass(kw_only=True)
class LegacyValuespec(FormSpec):
    varprefix: str
    type: str = "legacy_valuespec"
    input_html: Optional[str] = None
    readonly_html: Optional[str] = None


@dataclass(kw_only=True)
class String(FormSpec):
    type: str = "string"
    placeholder: Optional[str] = None
    input_hint: Optional[str] = None
    field_size: Optional[StringFieldSize] = None


@dataclass(kw_only=True)
class Password(FormSpec):
    password_store_choices: list[PasswordStoreChoice]
    i18n: I18nPassword
    type: str = "password"


@dataclass(kw_only=True)
class List(FormSpec):
    element_template: FormSpec
    element_default_value: Any
    editable_order: bool
    add_element_label: str
    remove_element_label: str
    no_element_label: str
    type: str = "list"


@dataclass(kw_only=True)
class DictionaryElement:
    ident: str
    required: bool
    default_value: Any
    parameter_form: FormSpec
    group: Optional[DictionaryGroup] = None


@dataclass(kw_only=True)
class Dictionary(FormSpec):
    groups: list[DictionaryGroup]
    type: str = "dictionary"
    elements: list[DictionaryElement] = field(default_factory=lambda: [])
    no_elements_text: Optional[str] = None
    additional_static_elements: Optional[dict[str, Any]] = None
    layout: DictionaryLayout = DictionaryLayout.one_column


@dataclass(kw_only=True)
class SingleChoice(FormSpec):
    frozen: bool
    input_hint: Any
    type: str = "single_choice"
    elements: list[SingleChoiceElement] = field(default_factory=lambda: [])
    no_elements_text: Optional[str] = None
    label: Optional[str] = None


@dataclass(kw_only=True)
class MultipleChoice(FormSpec):
    type: str = "multiple_choice"
    elements: list[MultipleChoiceElement] = field(default_factory=lambda: [])
    show_toggle_all: bool = False


@dataclass(kw_only=True)
class CascadingSingleChoiceElement:
    name: str
    title: str
    default_value: Any
    parameter_form: FormSpec


@dataclass(kw_only=True)
class CascadingSingleChoice(FormSpec):
    input_hint: Any
    type: str = "cascading_single_choice"
    elements: list[CascadingSingleChoiceElement] = field(default_factory=lambda: [])
    no_elements_text: Optional[str] = None
    label: Optional[str] = None
    layout: CascadingChoiceLayout = CascadingChoiceLayout.vertical


@dataclass(kw_only=True)
class FixedValue(FormSpec):
    value: Any
    type: str = "fixed_value"
    label: Optional[str] = None


@dataclass(kw_only=True)
class BooleanChoice(FormSpec):
    text_on: str
    text_off: str
    type: str = "boolean_choice"
    label: Optional[str] = None


@dataclass(kw_only=True)
class MultilineText(FormSpec):
    type: str = "multiline_text"
    label: Optional[str] = None
    macro_support: Optional[bool] = None
    monospaced: Optional[bool] = None
    input_hint: Optional[str] = None


@dataclass(kw_only=True)
class DataSize(FormSpec):
    displayed_magnitudes: list[str]
    type: str = "data_size"
    label: Optional[str] = None
    input_hint: Optional[str] = None


@dataclass(kw_only=True)
class Topic:
    key: str
    dictionary: Dictionary


@dataclass(kw_only=True)
class Catalog(FormSpec):
    topics: list[Topic]
    type: str = "catalog"


@dataclass(kw_only=True)
class TimeSpan(FormSpec):
    i18n: TimeSpanI18n
    displayed_magnitudes: list[TimeSpanTimeMagnitude]
    type: str = "time_span"
    label: Optional[str] = None
    input_hint: Optional[float] = None


Components = Union[
    Integer,
    Float,
    String,
    Dictionary,
    List,
    LegacyValuespec,
    SingleChoice,
    CascadingSingleChoice,
    FixedValue,
    BooleanChoice,
    MultilineText,
    Password,
    DataSize,
    Catalog,
    MultipleChoice,
    TimeSpan,
]


@dataclass(kw_only=True)
class VueFormspecComponents:
    components: Optional[Components] = None
    validation_message: Optional[ValidationMessage] = None
