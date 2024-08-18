#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal, TypeVar

import cmk.gui.form_specs.vue.shared_type_defs as VueComponents
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private import (
    Catalog,
    DictionaryExtended,
    LegacyValueSpec,
    ListExtended,
    SingleChoiceExtended,
    UnknownFormSpec,
)
from cmk.gui.form_specs.vue.type_defs import RenderMode
from cmk.gui.form_specs.vue.visitors.recomposers import (
    recompose_dictionary,
    recompose_host_state,
    recompose_list,
    recompose_percentage,
    recompose_regular_expression,
    recompose_service_state,
    recompose_single_choice,
    recompose_unknown_form_spec,
)
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DataSize,
    Dictionary,
    FixedValue,
    Float,
    FormSpec,
    HostState,
    Integer,
    List,
    MultilineText,
    Percentage,
    RegularExpression,
    ServiceState,
    SingleChoice,
    String,
)

from .registries import get_visitor, register_visitor_class
from .visitors import (
    BooleanChoiceVisitor,
    CascadingSingleChoiceVisitor,
    CatalogVisitor,
    DataSizeVisitor,
    DictionaryVisitor,
    FixedValueVisitor,
    FloatVisitor,
    IntegerVisitor,
    LegacyValuespecVisitor,
    ListVisitor,
    MultilineTextVisitor,
    SingleChoiceVisitor,
    StringVisitor,
)
from .visitors._type_defs import DataOrigin, DEFAULT_VALUE, VisitorOptions

T = TypeVar("T")


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    spec: VueComponents.FormSpec
    data: Any
    validation: Any
    render_mode: Literal["edit", "readonly", "both"]


def register_form_specs():
    # TODO: add test which checks if all available FormSpecs have a visitor
    # Native rendering
    register_visitor_class(Integer, IntegerVisitor)
    register_visitor_class(DictionaryExtended, DictionaryVisitor)
    register_visitor_class(String, StringVisitor)
    register_visitor_class(Float, FloatVisitor)
    register_visitor_class(SingleChoiceExtended, SingleChoiceVisitor)
    register_visitor_class(CascadingSingleChoice, CascadingSingleChoiceVisitor)
    register_visitor_class(LegacyValueSpec, LegacyValuespecVisitor)
    register_visitor_class(FixedValue, FixedValueVisitor)
    register_visitor_class(BooleanChoice, BooleanChoiceVisitor)
    register_visitor_class(MultilineText, MultilineTextVisitor)
    register_visitor_class(RegularExpression, StringVisitor, recompose_regular_expression)
    register_visitor_class(DataSize, DataSizeVisitor)
    register_visitor_class(Catalog, CatalogVisitor)
    register_visitor_class(ListExtended, ListVisitor)

    # Recomposed
    register_visitor_class(HostState, SingleChoiceVisitor, recompose_host_state)
    register_visitor_class(ServiceState, SingleChoiceVisitor, recompose_service_state)
    register_visitor_class(SingleChoice, SingleChoiceVisitor, recompose_single_choice)
    register_visitor_class(List, ListVisitor, recompose_list)
    register_visitor_class(Percentage, FloatVisitor, recompose_percentage)
    register_visitor_class(UnknownFormSpec, LegacyValuespecVisitor, recompose_unknown_form_spec)
    register_visitor_class(Dictionary, DictionaryVisitor, recompose_dictionary)


register_form_specs()


def _process_validation_errors(validation_errors: list[VueComponents.ValidationMessage]) -> None:
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
        "" if not first_error.location else first_error.location[-1], first_error.message
    )


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
    display_mode: RenderMode = RenderMode.EDIT,
) -> None:
    """Renders the valuespec via vue within a div"""
    vue_app_config = serialize_data_for_frontend(
        form_spec, field_id, origin, do_validate, value, display_mode
    )
    logger.warning("Vue app config:\n%s", pprint.pformat(vue_app_config, width=220, indent=2))
    logger.warning("Vue value:\n%s", pprint.pformat(vue_app_config.data, width=220))
    logger.warning("Vue validation:\n%s", pprint.pformat(vue_app_config.validation, width=220))
    html.div("", data_cmk_vue_app=json.dumps(asdict(vue_app_config)))


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
) -> Sequence[VueComponents.ValidationMessage]:
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    return visitor.validate(value_from_frontend)


def parse_value_from_frontend(form_spec: FormSpec[T], value_from_frontend: Any) -> Any:
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    return visitor.to_disk(value_from_frontend)


def serialize_data_for_frontend(
    form_spec: FormSpec[T],
    field_id: str,
    origin: DataOrigin,
    do_validate: bool,
    value: Any = DEFAULT_VALUE,
    render_mode: RenderMode = RenderMode.EDIT,
) -> VueAppConfig:
    """Serializes backend value to vue app compatible config."""
    visitor = get_visitor(form_spec, VisitorOptions(data_origin=origin))
    vue_component, vue_value = visitor.to_vue(value)

    validation: list[VueComponents.ValidationMessage] = []
    if do_validate:
        validation = visitor.validate(value)

    return VueAppConfig(
        id=field_id,
        app_name="form_spec",
        spec=vue_component,
        data=vue_value,
        validation=validation,
        render_mode=render_mode.value,
    )
