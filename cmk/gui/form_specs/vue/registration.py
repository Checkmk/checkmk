#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.form_specs.private.validators as private_form_specs_validators
import cmk.rulesets.v1.form_specs.validators as formspec_validators
from cmk.gui.form_specs.converter import (
    SimplePassword,
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.form_specs.private import (
    CascadingSingleChoiceExtended,
    Catalog,
    CommentTextArea,
    ConditionChoices,
    DictionaryExtended,
    Labels,
    LegacyValueSpec,
    ListExtended,
    ListOfStrings,
    ListUniqueSelection,
    MetricExtended,
    MultipleChoiceExtended,
    OptionalChoice,
    SingleChoiceEditable,
    SingleChoiceExtended,
    StringAutocompleter,
    TimeSpecific,
    UserSelection,
)
from cmk.gui.form_specs.private.two_column_dictionary import TwoColumnDictionary
from cmk.gui.form_specs.vue.visitors.condition_choices import ConditionChoicesVisitor
from cmk.gui.form_specs.vue.visitors.metric import MetricVisitor
from cmk.gui.form_specs.vue.visitors.recomposers import (
    recompose_cascading_single_choice,
    recompose_dictionary,
    recompose_host_state,
    recompose_levels,
    recompose_list,
    recompose_metric,
    recompose_monitored_host,
    recompose_monitored_service,
    recompose_multiple_choice,
    recompose_percentage,
    recompose_proxy,
    recompose_regular_expression,
    recompose_service_state,
    recompose_single_choice,
    recompose_string,
    recompose_time_period,
    recompose_user_selection,
)
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DataSize,
    Dictionary,
    FileUpload,
    FixedValue,
    Float,
    HostState,
    Integer,
    Levels,
    List,
    Metric,
    MonitoredHost,
    MonitoredService,
    MultilineText,
    MultipleChoice,
    Password,
    Percentage,
    Proxy,
    RegularExpression,
    ServiceState,
    SimpleLevels,
    SingleChoice,
    String,
    TimePeriod,
    TimeSpan,
)

from ._registry import register_recomposer_function, register_visitor_class
from .validators import (
    build_float_validator,
    build_in_range_validator,
    build_integer_validator,
    build_length_in_range_validator,
    register_validator,
)
from .visitors import (
    BooleanChoiceVisitor,
    CascadingSingleChoiceVisitor,
    CatalogVisitor,
    CommentTextAreaVisitor,
    DataSizeVisitor,
    DictionaryVisitor,
    FileUploadVisitor,
    FixedValueVisitor,
    FloatVisitor,
    IntegerVisitor,
    LabelsVisitor,
    LegacyValuespecVisitor,
    ListOfStringsVisitor,
    ListUniqueSelectionVisitor,
    ListVisitor,
    MultilineTextVisitor,
    MultipleChoiceVisitor,
    OptionalChoiceVisitor,
    PasswordVisitor,
    SimplePasswordVisitor,
    SingleChoiceEditableVisitor,
    SingleChoiceVisitor,
    StringVisitor,
    TimeSpanVisitor,
    TimeSpecificVisitor,
    TransformVisitor,
    TupleVisitor,
    TwoColumnDictionaryVisitor,
)


def register() -> None:
    register_form_specs()
    register_validators()


def register_form_specs() -> None:
    # TODO: add test which checks if all available FormSpecs have a visitor
    # Native rendering
    register_visitor_class(Integer, IntegerVisitor)
    register_visitor_class(DictionaryExtended, DictionaryVisitor)
    register_visitor_class(TwoColumnDictionary, TwoColumnDictionaryVisitor)
    register_visitor_class(String, StringVisitor)
    register_visitor_class(Float, FloatVisitor)
    register_visitor_class(SingleChoiceExtended, SingleChoiceVisitor)
    register_visitor_class(SingleChoiceEditable, SingleChoiceEditableVisitor)
    register_visitor_class(Password, PasswordVisitor)
    register_visitor_class(CascadingSingleChoiceExtended, CascadingSingleChoiceVisitor)
    register_visitor_class(LegacyValueSpec, LegacyValuespecVisitor)
    register_visitor_class(FixedValue, FixedValueVisitor)
    register_visitor_class(BooleanChoice, BooleanChoiceVisitor)
    register_visitor_class(MetricExtended, MetricVisitor)
    register_visitor_class(MultilineText, MultilineTextVisitor)
    register_visitor_class(CommentTextArea, CommentTextAreaVisitor)
    register_visitor_class(DataSize, DataSizeVisitor)
    register_visitor_class(Catalog, CatalogVisitor)
    register_visitor_class(ListExtended, ListVisitor)
    register_visitor_class(ListUniqueSelection, ListUniqueSelectionVisitor)
    register_visitor_class(TimeSpan, TimeSpanVisitor)
    register_visitor_class(TransformDataForLegacyFormatOrRecomposeFunction, TransformVisitor)
    register_visitor_class(Tuple, TupleVisitor)
    register_visitor_class(OptionalChoice, OptionalChoiceVisitor)
    register_visitor_class(SimplePassword, SimplePasswordVisitor)
    register_visitor_class(StringAutocompleter, StringVisitor)
    register_visitor_class(ConditionChoices, ConditionChoicesVisitor)
    register_visitor_class(ListOfStrings, ListOfStringsVisitor)
    register_visitor_class(MultipleChoiceExtended, MultipleChoiceVisitor)
    register_visitor_class(Labels, LabelsVisitor)
    register_visitor_class(TimeSpecific, TimeSpecificVisitor)
    register_visitor_class(FileUpload, FileUploadVisitor)

    # Recomposed
    register_recomposer_function(RegularExpression, recompose_regular_expression)
    register_recomposer_function(MultipleChoice, recompose_multiple_choice)
    register_recomposer_function(Metric, recompose_metric)
    register_recomposer_function(MonitoredHost, recompose_monitored_host)
    register_recomposer_function(MonitoredService, recompose_monitored_service)
    register_recomposer_function(String, recompose_string)
    register_recomposer_function(HostState, recompose_host_state)
    register_recomposer_function(ServiceState, recompose_service_state)
    register_recomposer_function(SingleChoice, recompose_single_choice)
    register_recomposer_function(Levels, recompose_levels)
    register_recomposer_function(SimpleLevels, recompose_levels)
    register_recomposer_function(List, recompose_list)
    register_recomposer_function(Percentage, recompose_percentage)
    register_recomposer_function(UserSelection, recompose_user_selection)
    register_recomposer_function(Dictionary, recompose_dictionary)
    register_recomposer_function(CascadingSingleChoice, recompose_cascading_single_choice)
    register_recomposer_function(Proxy, recompose_proxy)
    register_recomposer_function(TimePeriod, recompose_time_period)


def register_validators() -> None:
    register_validator(formspec_validators.NumberInRange, build_in_range_validator)
    register_validator(formspec_validators.LengthInRange, build_length_in_range_validator)
    register_validator(private_form_specs_validators.IsInteger, build_integer_validator)
    register_validator(private_form_specs_validators.IsFloat, build_float_validator)
