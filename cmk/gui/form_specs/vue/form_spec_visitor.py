#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, TypeVar

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _

import cmk.gui.form_specs.private.validators as private_form_specs_validators
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
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
    MonitoredHostExtended,
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
    recompose_monitored_host_extended,
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
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger

import cmk.rulesets.v1.form_specs.validators as formspec_validators
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DataSize,
    Dictionary,
    FileUpload,
    FixedValue,
    Float,
    FormSpec,
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
from cmk.shared_typing import vue_formspec_components as shared_type_defs

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
    get_visitor,
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
    register_recomposer_function,
    register_visitor_class,
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
from .visitors._type_defs import (
    DataOrigin,
    DEFAULT_VALUE,
    DefaultValue,
    DiskModel,
    VisitorOptions,
)
from .visitors._type_defs import FormSpecValidationError as FormSpecValidationError

T = TypeVar("T")
_FrontendModel = TypeVar("_FrontendModel")


class DisplayMode(Enum):
    EDIT = "edit"
    READONLY = "readonly"
    BOTH = "both"


class RenderMode(Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    BACKEND_AND_FRONTEND = "backend_and_frontend"


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    spec: shared_type_defs.FormSpec
    data: Any
    validation: Any
    display_mode: str


def register_form_specs():
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
    register_recomposer_function(MonitoredHostExtended, recompose_monitored_host_extended)
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


def register_validators():
    register_validator(formspec_validators.NumberInRange, build_in_range_validator)
    register_validator(formspec_validators.LengthInRange, build_length_in_range_validator)
    register_validator(private_form_specs_validators.IsInteger, build_integer_validator)
    register_validator(private_form_specs_validators.IsFloat, build_float_validator)


register_form_specs()
register_validators()


def _process_validation_errors(
    validation_errors: list[shared_type_defs.ValidationMessage],
) -> None:
    """This functions introduces validation errors from the vue-world into the CheckMK-GUI-world
    The CheckMK-GUI works with a global parameter user_errors.
    These user_errors include the field_id of the broken input field and the error text
    """
    # TODO: this function will become obsolete once all errors are shown within the form spec
    #       and valuespecs render_input no longer relies on the varprefixes in user_errors
    if not validation_errors:
        return

    first_error = validation_errors[0]
    raise MKUserError(
        "" if not first_error.location else first_error.location[-1],
        _("Cannot save the form because it contains errors."),
    )


def process_validation_messages(
    validation_messages: list[shared_type_defs.ValidationMessage],
) -> None:
    """Helper function to process validation errors in general use cases.

    Args:
        validation_messages: Validation messages returned by Visitor.validate

    Raises:
        FormSpecValidationError: An error storing the validation messages
    """
    if validation_messages:
        raise FormSpecValidationError(validation_messages)


def get_vue_value(field_id: str, fallback_value: Any) -> Any:
    """Returns the value of a vue formular field"""
    if request.has_var(field_id):
        return json.loads(request.get_str_input_mandatory(field_id))
    return fallback_value


def render_form_spec(
    form_spec: FormSpec[T],
    field_id: str,
    value: Any,
    origin: DataOrigin,
    do_validate: bool,
    display_mode: DisplayMode = DisplayMode.EDIT,
) -> None:
    """Renders the valuespec via vue within a div"""
    vue_app_config = serialize_data_for_frontend(
        form_spec, field_id, origin, do_validate, value, display_mode
    )
    if active_config.load_frontend_vue == "inject":
        logger.warning(
            "Vue app config:\n%s", pprint.pformat(asdict(vue_app_config), width=220, indent=2)
        )
        logger.warning("Vue value:\n%s", pprint.pformat(vue_app_config.data, width=220))
        logger.warning("Vue validation:\n%s", pprint.pformat(vue_app_config.validation, width=220))
    html.vue_component(component_name="cmk-form-spec", data=asdict(vue_app_config))


def parse_data_from_frontend(form_spec: FormSpec[T], field_id: str) -> Any:
    """Computes/validates the value from a vue formular field"""
    if not request.has_var(field_id):
        raise MKGeneralException("Formular data is missing in request")
    value_from_frontend = json.loads(request.get_str_input_mandatory(field_id))
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    _process_validation_errors(visitor.validate(value_from_frontend))
    return visitor.to_disk(value_from_frontend)


def validate_value_from_frontend(
    form_spec: FormSpec[T], value_from_frontend: Any
) -> Sequence[shared_type_defs.ValidationMessage]:
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    return visitor.validate(value_from_frontend)


def transform_to_disk_model(
    form_spec: FormSpec[T], value_from_frontend: _FrontendModel | DefaultValue = DEFAULT_VALUE
) -> DiskModel:
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    return visitor.to_disk(value_from_frontend)


def serialize_data_for_frontend(
    form_spec: FormSpec[T],
    field_id: str,
    origin: DataOrigin,
    do_validate: bool,
    value: Any = DEFAULT_VALUE,
    display_mode: DisplayMode = DisplayMode.EDIT,
) -> VueAppConfig:
    """Serializes backend value to vue app compatible config."""
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=origin))
    vue_component, vue_value = visitor.to_vue(value)

    validation: list[shared_type_defs.ValidationMessage] = []
    if do_validate:
        validation = visitor.validate(value)

    return VueAppConfig(
        id=field_id,
        spec=vue_component,
        data=vue_value,
        validation=validation,
        display_mode=display_mode.value,
    )
