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


@dataclass(kw_only=True)
class DualListChoiceI18n:
    add: str
    remove: str
    add_all: str
    remove_all: str
    available_options: str
    selected_options: str
    selected: str
    no_elements_available: str
    no_elements_selected: str


class CascadingChoiceLayout(str, Enum):
    vertical = "vertical"
    horizontal = "horizontal"


@dataclass(kw_only=True)
class CommentTextAreaI18n:
    prefix_date_and_comment: str


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


class TupleLayout(str, Enum):
    horizontal_titles_top = "horizontal_titles_top"
    horizontal = "horizontal"
    vertical = "vertical"
    float = "float"


@dataclass(kw_only=True)
class I18nOptionalChoice:
    label: Optional[str] = None
    none_label: Optional[str] = None


@dataclass(kw_only=True)
class Autocompleter:
    data: dict[str, Any]
    fetch_method: str = "ajax_vs_autocomplete"


class ListOfStringsLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


@dataclass(kw_only=True)
class ValidationMessage:
    location: list[str]
    message: str
    invalid_value: Any


@dataclass(kw_only=True)
class FallbackWarningI18n:
    title: str
    message: str
    setup_link_title: str
    do_not_show_again_title: str


@dataclass(kw_only=True)
class NotificationStatsI18n:
    sent_notifications: str
    failed_notifications: str
    sent_notifications_link_title: str
    failed_notifications_link_title: str


@dataclass(kw_only=True)
class CoreStatsI18n:
    title: str
    sites_column_title: str
    status_column_title: str
    ok_msg: str
    warning_msg: str
    disabled_msg: str


@dataclass(kw_only=True)
class Rule:
    i18n: str
    count: str
    link: str


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
    autocompleter: Optional[Autocompleter] = None


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
class DualListChoice(FormSpec):
    i18n: DualListChoiceI18n
    elements: Optional[list[MultipleChoiceElement]] = field(default_factory=lambda: [])
    show_toggle_all: Optional[bool] = False
    type: str = "dual_list_choice"


@dataclass(kw_only=True)
class CheckboxListChoice(FormSpec):
    type: str = "checkbox_list_choice"
    elements: Optional[list[MultipleChoiceElement]] = field(default_factory=lambda: [])


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
    label: Optional[str] = None
    macro_support: Optional[bool] = None
    monospaced: Optional[bool] = None
    input_hint: Optional[str] = None
    type: str = "multiline_text"


@dataclass(kw_only=True)
class CommentTextArea(MultilineText):
    user_name: str
    i18n: CommentTextAreaI18n
    type: str = "comment_text_area"


@dataclass(kw_only=True)
class DataSize(FormSpec):
    displayed_magnitudes: list[str]
    type: str = "data_size"
    label: Optional[str] = None
    input_hint: Optional[str] = None


@dataclass(kw_only=True)
class Topic:
    ident: str
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


@dataclass(kw_only=True)
class Tuple(FormSpec):
    elements: list[FormSpec]
    type: str = "tuple"
    layout: TupleLayout = TupleLayout.vertical
    show_titles: Optional[bool] = True


@dataclass(kw_only=True)
class OptionalChoice(FormSpec):
    parameter_form: FormSpec
    i18n: I18nOptionalChoice
    parameter_form_default_value: Any
    type: str = "optional_choice"


@dataclass(kw_only=True)
class SimplePassword(FormSpec):
    type: str = "simple_password"


@dataclass(kw_only=True)
class ListOfStrings(FormSpec):
    string_spec: FormSpec
    type: str = "list_of_strings"
    string_default_value: Optional[str] = ""
    layout: Optional[ListOfStringsLayout] = ListOfStringsLayout.horizontal


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
    CommentTextArea,
    Password,
    DataSize,
    Catalog,
    DualListChoice,
    CheckboxListChoice,
    TimeSpan,
    Tuple,
    OptionalChoice,
    SimplePassword,
    ListOfStrings,
]


@dataclass(kw_only=True)
class FallbackWarning:
    i18n: FallbackWarningI18n
    user_id: str
    setup_link: str
    do_not_show_again_link: str


@dataclass(kw_only=True)
class NotificationStats:
    num_sent_notifications: int
    num_failed_notifications: int
    sent_notification_link: str
    failed_notification_link: str
    i18n: NotificationStatsI18n


@dataclass(kw_only=True)
class CoreStats:
    sites: list[str]
    i18n: CoreStatsI18n


@dataclass(kw_only=True)
class RuleTopic:
    rules: list[Rule]
    i18n: Optional[str] = None


@dataclass(kw_only=True)
class RuleSection:
    i18n: str
    topics: list[RuleTopic]


@dataclass(kw_only=True)
class Notifications:
    notification_stats: NotificationStats
    core_stats: CoreStats
    rule_sections: list[RuleSection]
    fallback_warning: Optional[FallbackWarning] = None


@dataclass(kw_only=True)
class NotificationParametersOverview:
    parameters: list[RuleSection]


@dataclass(kw_only=True)
class VueFormspecComponents:
    components: Optional[Components] = None
    validation_message: Optional[ValidationMessage] = None
    notifications: Optional[Notifications] = None
    notifications_parameters_overview: Optional[NotificationParametersOverview] = None
