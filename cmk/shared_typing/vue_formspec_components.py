#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.
#
# fmt: off


from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


@dataclass(kw_only=True)
class IsInteger:
    error_message: str
    type: str = "is_integer"


@dataclass(kw_only=True)
class IsFloat:
    error_message: str
    type: str = "is_float"


@dataclass(kw_only=True)
class LengthInRange:
    min_value: Optional[int]
    max_value: Optional[int]
    error_message: str
    type: str = "length_in_range"


@dataclass(kw_only=True)
class NumberInRange:
    min_value: Optional[float]
    max_value: Optional[float]
    error_message: str
    type: str = "number_in_range"


@dataclass(kw_only=True)
class MatchRegex:
    type: str = "match_regex"
    regex: Optional[str] = None
    error_message: Optional[str] = None


Validator = Union[IsInteger, IsFloat, NumberInRange, LengthInRange, MatchRegex]


@dataclass(kw_only=True)
class I18nFormSpecBase:
    required: str


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
    choose_password_from_store: str
    choose_password_type: str


class DictionaryGroupLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


@dataclass(kw_only=True)
class DictionaryGroup:
    key: Optional[str]
    title: Optional[str]
    help: Optional[str]
    layout: DictionaryGroupLayout


class DictionaryLayout(str, Enum):
    one_column = "one_column"
    two_columns = "two_columns"


@dataclass(kw_only=True)
class SingleChoiceElement:
    name: str
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
    autocompleter_loading: str
    search_available_options: str
    search_selected_options: str
    and_x_more: str


class CascadingSingleChoiceLayout(str, Enum):
    vertical = "vertical"
    horizontal = "horizontal"
    button_group = "button_group"


@dataclass(kw_only=True)
class FileUploadI18n:
    replace_file: str


@dataclass(kw_only=True)
class CommentTextAreaI18n:
    prefix_date_and_comment: str


@dataclass(kw_only=True)
class MetricI18n:
    host_input_hint: str
    host_filter: str
    service_input_hint: str
    service_filter: str


@dataclass(kw_only=True)
class DataSizeI18n:
    choose_unit: str


@dataclass(kw_only=True)
class TimeSpanI18n:
    millisecond: str
    second: str
    minute: str
    hour: str
    day: str
    validation_negative_number: str


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
    label: str
    none_label: str


@dataclass(kw_only=True)
class SingleChoiceEditableI18n:
    slidein_save_button: str
    slidein_cancel_button: str
    slidein_create_button: str
    slidein_new_title: str
    slidein_edit_title: str
    edit: str
    create: str
    loading: str
    no_objects: str
    no_selection: str
    validation_error: str
    fatal_error: str
    fatal_error_reload: str


@dataclass(kw_only=True)
class AutocompleterParams:
    show_independent_of_context: Optional[bool] = None
    strict: Optional[bool] = None
    escape_regex: Optional[bool] = None
    world: Optional[str] = None
    context: Optional[dict[str, Any]] = None


@dataclass(kw_only=True)
class AutocompleterData:
    ident: str
    params: AutocompleterParams


@dataclass(kw_only=True)
class Autocompleter:
    data: AutocompleterData
    fetch_method: str = "ajax_vs_autocomplete"


class ListOfStringsLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


@dataclass(kw_only=True)
class Condition:
    name: str
    title: str


@dataclass(kw_only=True)
class ConditionGroup:
    title: str
    conditions: list[Condition]


@dataclass(kw_only=True)
class ConditionChoicesI18n:
    choose_operator: str
    choose_condition: str
    add_condition_label: str
    select_condition_group_to_add: str
    no_more_condition_groups_to_add: str
    eq_operator: str
    ne_operator: str
    or_operator: str
    nor_operator: str


@dataclass(kw_only=True)
class LabelsI18n:
    add_some_labels: str
    remove_label: str
    key_value_format_error: str
    uniqueness_error: str
    max_labels_reached: str


class LabelSource(str, Enum):
    explicit = "explicit"
    ruleset = "ruleset"
    discovered = "discovered"


@dataclass(kw_only=True)
class TimeSpecificI18n:
    enable: str
    disable: str


@dataclass(kw_only=True)
class ValidationMessage:
    location: list[str]
    message: str
    invalid_value: Any


@dataclass(kw_only=True)
class Eq:
    oper_eq: str


@dataclass(kw_only=True)
class Ne:
    oper_ne: str


@dataclass(kw_only=True)
class Or:
    oper_or: list[str]


@dataclass(kw_only=True)
class Nor:
    oper_nor: list[str]


@dataclass(kw_only=True)
class ConditionChoicesValue:
    group_name: str
    value: Union[Eq, Ne, Or, Nor]


Values = ConditionChoicesValue


@dataclass(kw_only=True)
class FormSpec:
    type: str
    title: str
    help: str
    validators: list[Validator]


@dataclass(kw_only=True)
class Integer(FormSpec):
    label: Optional[str]
    unit: Optional[str]
    input_hint: Optional[str]
    i18n_base: I18nFormSpecBase
    type: str = "integer"


@dataclass(kw_only=True)
class Float(FormSpec):
    label: Optional[str]
    unit: Optional[str]
    input_hint: Optional[str]
    i18n_base: I18nFormSpecBase
    type: str = "float"


@dataclass(kw_only=True)
class LegacyValuespec(FormSpec):
    varprefix: str
    type: str = "legacy_valuespec"


@dataclass(kw_only=True)
class String(FormSpec):
    label: Optional[str]
    input_hint: Optional[str]
    field_size: StringFieldSize
    autocompleter: Optional[Autocompleter]
    i18n_base: I18nFormSpecBase
    type: str = "string"


@dataclass(kw_only=True)
class Password(FormSpec):
    password_store_choices: list[PasswordStoreChoice]
    i18n: I18nPassword
    i18n_base: I18nFormSpecBase
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
    name: str
    required: bool
    group: Optional[DictionaryGroup]
    default_value: Any
    render_only: bool
    parameter_form: FormSpec


@dataclass(kw_only=True)
class Dictionary(FormSpec):
    groups: list[DictionaryGroup]
    no_elements_text: str
    additional_static_elements: Optional[dict[str, Any]]
    i18n_base: I18nFormSpecBase
    type: str = "dictionary"
    elements: list[DictionaryElement] = field(default_factory=lambda: [])
    layout: DictionaryLayout = DictionaryLayout.one_column


@dataclass(kw_only=True)
class SingleChoice(FormSpec):
    no_elements_text: Optional[str]
    frozen: bool
    label: Optional[str]
    input_hint: Optional[str]
    i18n_base: I18nFormSpecBase
    type: str = "single_choice"
    elements: list[SingleChoiceElement] = field(default_factory=lambda: [])


@dataclass(kw_only=True)
class DualListChoice(FormSpec):
    i18n: DualListChoiceI18n
    elements: Optional[list[MultipleChoiceElement]] = field(default_factory=lambda: [])
    show_toggle_all: Optional[bool] = False
    autocompleter: Optional[Autocompleter] = None
    type: str = "dual_list_choice"


@dataclass(kw_only=True)
class CheckboxListChoice(FormSpec):
    i18n: DualListChoiceI18n
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
    label: Optional[str]
    input_hint: Optional[str]
    i18n_base: I18nFormSpecBase
    type: str = "cascading_single_choice"
    elements: list[CascadingSingleChoiceElement] = field(default_factory=lambda: [])
    layout: CascadingSingleChoiceLayout = CascadingSingleChoiceLayout.vertical


@dataclass(kw_only=True)
class FileUpload(FormSpec):
    i18n: FileUploadI18n
    type: str = "file_upload"


@dataclass(kw_only=True)
class FixedValue(FormSpec):
    label: Optional[str]
    value: Any
    type: str = "fixed_value"


@dataclass(kw_only=True)
class BooleanChoice(FormSpec):
    label: Optional[str]
    text_on: str
    text_off: str
    type: str = "boolean_choice"


@dataclass(kw_only=True)
class MultilineText(FormSpec):
    label: Optional[str]
    macro_support: bool
    monospaced: bool
    input_hint: Optional[str]
    type: str = "multiline_text"


@dataclass(kw_only=True)
class CommentTextArea(MultilineText):
    user_name: str
    i18n: CommentTextAreaI18n
    type: str = "comment_text_area"


@dataclass(kw_only=True)
class Metric(String):
    service_filter_autocompleter: Autocompleter
    host_filter_autocompleter: Autocompleter
    i18n: MetricI18n
    type: str = "metric"


@dataclass(kw_only=True)
class DataSize(FormSpec):
    label: Optional[str]
    displayed_magnitudes: list[str]
    input_hint: Optional[str]
    i18n: DataSizeI18n
    type: str = "data_size"


@dataclass(kw_only=True)
class TopicElement:
    name: str
    required: bool
    parameter_form: FormSpec
    default_value: Any
    type: str = "topic_element"


@dataclass(kw_only=True)
class TimeSpan(FormSpec):
    label: Optional[str]
    i18n: TimeSpanI18n
    displayed_magnitudes: list[TimeSpanTimeMagnitude]
    input_hint: Optional[float]
    type: str = "time_span"


@dataclass(kw_only=True)
class Tuple(FormSpec):
    elements: list[FormSpec]
    show_titles: bool
    type: str = "tuple"
    layout: TupleLayout = TupleLayout.vertical


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
class SingleChoiceEditable(FormSpec):
    config_entity_type: str
    config_entity_type_specifier: str
    elements: list[SingleChoiceElement]
    allow_editing_existing_elements: bool
    i18n: SingleChoiceEditableI18n
    i18n_base: I18nFormSpecBase
    type: str = "single_choice_editable"


@dataclass(kw_only=True)
class ListOfStrings(FormSpec):
    string_spec: FormSpec
    type: str = "list_of_strings"
    string_default_value: Optional[str] = ""
    layout: Optional[ListOfStringsLayout] = ListOfStringsLayout.horizontal


@dataclass(kw_only=True)
class ConditionChoices(FormSpec):
    condition_groups: dict[str, ConditionGroup]
    i18n: ConditionChoicesI18n
    i18n_base: I18nFormSpecBase
    type: str = "condition_choices"


@dataclass(kw_only=True)
class Labels(FormSpec):
    i18n: LabelsI18n
    autocompleter: Autocompleter
    max_labels: Optional[int]
    label_source: Optional[LabelSource]
    type: str = "labels"


@dataclass(kw_only=True)
class TimeSpecific(FormSpec):
    i18n: TimeSpecificI18n
    parameter_form_enabled: FormSpec
    parameter_form_disabled: FormSpec
    type: str = "time_specific"
    time_specific_values_key: str = "tp_values"
    default_value_key: str = "tp_default_value"


@dataclass(kw_only=True)
class ListUniqueSelection(FormSpec):
    element_template: Union[SingleChoice, CascadingSingleChoice]
    element_default_value: Any
    add_element_label: str
    remove_element_label: str
    no_element_label: str
    unique_selection_elements: list[str]
    type: str = "list_unique_selection"


@dataclass(kw_only=True)
class TopicGroup:
    title: str
    elements: list[TopicElement]
    type: str = "topic_group"


@dataclass(kw_only=True)
class Topic:
    name: str
    title: str
    elements: Union[list[TopicGroup], list[TopicElement]]


@dataclass(kw_only=True)
class Catalog(FormSpec):
    elements: list[Topic]
    i18n_base: I18nFormSpecBase
    type: str = "catalog"


Components = Union[
    Integer,
    Float,
    String,
    Dictionary,
    List,
    ListUniqueSelection,
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
    Metric,
    SingleChoiceEditable,
    Tuple,
    OptionalChoice,
    SimplePassword,
    ListOfStrings,
    ConditionChoices,
    Labels,
    FileUpload,
    TimeSpecific,
]


@dataclass(kw_only=True)
class VueFormspecComponents:
    components: Optional[Components] = None
    validation_message: Optional[ValidationMessage] = None
    values: Optional[Values] = None
