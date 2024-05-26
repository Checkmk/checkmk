#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import auto, Enum
from typing import Any, TypeVar

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private.validators import IsInteger
from cmk.gui.form_specs.vue.type_defs.vue_formspec_components import (
    VueDictionary,
    VueDictionaryElement,
    VueInteger,
    VueSchema,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.utils.user_errors import user_errors

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    Dictionary,
    Float,
    FormSpec,
    Integer,
    List,
    Percentage,
    ServiceState,
    SingleChoice,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError

ModelT = TypeVar("ModelT")

# TODO: improve typing
DataForDisk = Any
Value = Any


@dataclass(kw_only=True)
class Validation:
    location: list
    message: str


class DataOrigin(Enum):
    DISK = auto()
    FRONTEND = auto()


@dataclass
class VisitorOptions:
    data_mode: DataOrigin
    validate: bool


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    form_spec: VueSchema
    model_value: Any
    validation_messages: Any


VueVisitorMethodResult = tuple[VueSchema, Value, list[Validation], DataForDisk]
VueFormSpecVisitorMethod = Callable[[VisitorOptions, Any, Any], VueVisitorMethodResult]


######## DEBUG STUFF START ################
_debug_indent = 0


@contextmanager
def _change_log_indent(size):
    global _debug_indent
    try:
        _debug_indent += size
        yield
    finally:
        _debug_indent -= size


def _log_indent(info):
    logger.warning(" " * _debug_indent + info)


######## DEBUG STUFF END ################


def _visit(
    visitor_options: VisitorOptions, form_spec: FormSpec, value: Any
) -> VueVisitorMethodResult:
    basic_form_spec = _convert_to_supported_form_spec(form_spec)

    visitor_method: VueFormSpecVisitorMethod = _get_visitor_method(basic_form_spec)
    if visitor_options.data_mode == DataOrigin.DISK and basic_form_spec.migrate:
        value = basic_form_spec.migrate(value)
    return visitor_method(visitor_options, basic_form_spec, value)


def _get_visitor_method(form_spec: FormSpec) -> VueFormSpecVisitorMethod:
    visitor_function = _form_specs_visitor_registry.get(form_spec.__class__)
    if visitor_function is None:
        raise MKGeneralException(f"No visitor for {form_spec.__class__.__name__}")
    return visitor_function


def _get_title_and_help(form_spec: FormSpec) -> tuple[str, str]:
    title = (
        "" if form_spec.title is None else form_spec.title.localize(translate_to_current_language)
    )
    help_text = (
        ""
        if form_spec.help_text is None
        else form_spec.help_text.localize(translate_to_current_language)
    )
    return title, help_text


def _optional_validation(validators: list[Callable[[ModelT], object]], raw_value: Any) -> list[str]:
    validation_errors = []
    for validator in validators:
        try:
            validator(raw_value)
        except ValidationError as e:
            validation_errors.append(e.message.localize(translate_to_current_language))
            # The aggregated errors are used within our old GUI which
            # requires the MKUser error format (field_id + message)
            # self._aggregated_validation_errors.add(e.message)
            # TODO: add external validation errors for legacy formspecs
            #       or handle it within the form_spec_valuespec_wrapper
    return validation_errors


def _visit_integer(
    visitor_options: VisitorOptions, form_spec: Integer, value: int
) -> VueVisitorMethodResult:
    title, help_text = _get_title_and_help(form_spec)

    validators = [IsInteger()] + (
        list(form_spec.custom_validate) if form_spec.custom_validate else []
    )
    validation_errors = []
    if visitor_options.validate:
        validation_errors = list(
            Validation(location=[""], message=x)
            for x in _optional_validation(validators, value)
            if x is not None
        )

    result = (
        VueInteger(title=title, help=help_text, validators=build_vue_validators(validators)),
        value,
        validation_errors,
        value,
    )
    return result


def _visit_dictionary(
    visitor_options: VisitorOptions, form_spec: Dictionary, value: dict[str, Any]
) -> VueVisitorMethodResult:
    title, help_text = _get_title_and_help(form_spec)
    elements_keyspec = []
    vue_values = {}
    element_validations = []
    disk_values = {}

    for key_name, dict_element in form_spec.elements.items():
        is_active = key_name in value
        key_value = (
            value[key_name] if is_active else _compute_default_value(dict_element.parameter_form)
        )

        element_schema, vue_value, vue_validation, disk_value = _visit(
            visitor_options, dict_element.parameter_form, key_value
        )

        for validation in vue_validation:
            element_validations.append(
                Validation(
                    location=[key_name] + validation.location,
                    message=validation.message,
                )
            )

        if is_active:
            disk_values[key_name] = disk_value
            vue_values[key_name] = key_value

        elements_keyspec.append(
            VueDictionaryElement(
                ident=key_name,
                default_value=vue_value,
                required=dict_element.required,
                vue_schema=element_schema,
            )
        )

    return (
        VueDictionary(title=title, help=help_text, elements=elements_keyspec),
        vue_values,
        element_validations,
        disk_values,
    )


_form_specs_visitor_registry: dict[type, VueFormSpecVisitorMethod] = {}


def register_class(validator_class: type, visitor_function: VueFormSpecVisitorMethod) -> None:
    _form_specs_visitor_registry[validator_class] = visitor_function


def register_form_specs():
    # TODO: add test which checks if all available FormSpecs have a visitor
    register_class(Integer, _visit_integer)
    register_class(Dictionary, _visit_dictionary)


register_form_specs()

# Vue is able to render these types in the frontend
VueFormSpecTypes = (
    Integer
    #    | Float
    #    | Percentage
    | String
    #    | SingleChoice
    #    | CascadingSingleChoice
    | Dictionary
    #    | List
    #    | ValueSpecFormSpec
)


def _convert_to_supported_form_spec(custom_form_spec: FormSpec) -> VueFormSpecTypes:
    if isinstance(custom_form_spec, VueFormSpecTypes):  # type: ignore[misc, arg-type]
        # These FormSpec types can be rendered by vue natively
        return custom_form_spec  # type: ignore[return-value]

    # All other types require a conversion to the basic types
    if isinstance(custom_form_spec, ServiceState):
        # TODO handle ServiceState
        String(title=Title("UNKNOWN custom_form_spec ServiceState"))

    # If no explicit conversion exist, create an ugly valuespec
    # TODO: raise an exception
    return String(title=Title("UNKNOWN custom_form_spec %s") % str(custom_form_spec))


# TODO: move this into the visiting function
def _compute_default_value(form_spec: FormSpec) -> Any:
    form_spec = _convert_to_supported_form_spec(form_spec)
    if isinstance(form_spec, (Integer, Percentage, Float)):
        return form_spec.prefill.value
    if isinstance(form_spec, CascadingSingleChoice):
        return form_spec.prefill.value
    if isinstance(form_spec, SingleChoice):
        return form_spec.prefill.value
    if isinstance(form_spec, List):
        return []
    if isinstance(form_spec, Dictionary):
        # TODO: Enable active keys
        return {}
    if isinstance(form_spec, String):
        return form_spec.prefill.value

    return "##################MISSING DEFAULT VALUE##########################"


def _process_validation_errors(validation_errors: list[Validation]) -> None:
    """This functions introduces validation errors from the vue-world into the CheckMK-GUI-world
    The CheckMK-GUI works with a global parameter user_errors.
    These user_errors include the field_id of the broken input field and the error text
    """
    # TODO: this function will become obsolete once all errors are shown within the form spec
    if not validation_errors:
        return

    # Our current error handling can only show one error at a time in the red error box.
    # This is just a quickfix
    for error in validation_errors[1:]:
        user_errors.add(MKUserError("", error.message))

    first_error = validation_errors[0]
    raise MKUserError("", first_error.message)


def render_form_spec(form_spec: FormSpec, field_id: str, default_value: Any) -> None:
    """Renders the valuespec via vue within a div"""
    if request.has_var(field_id):
        value = json.loads(request.get_str_input_mandatory(field_id))
        do_validate = True
    else:
        value = default_value
        do_validate = False

    try:
        schema, vue_value, validation, _data_for_disk = _visit(
            VisitorOptions(data_mode=DataOrigin.DISK, validate=do_validate), form_spec, value
        )
        vue_app_config = asdict(
            VueAppConfig(
                id=field_id,
                app_name="form_spec",
                form_spec=schema,
                model_value=vue_value,
                validation_messages=validation,
            )
        )
        logger.warning(pprint.pformat(vue_app_config))
        # logger.warning(f"Vue app config:\n{pprint.pformat(vue_visitor.vue_schema, width=220)}")
        # logger.warning(f"Vue value:\n{pprint.pformat(vue_visitor.value, width=220)}")
        # logger.warning(f"Disk value:\n{pprint.pformat(vue_visitor.data_for_disk, width=220)}")
        html.div("", data_cmk_vue_app=json.dumps(vue_app_config))
    except Exception as e:
        logger.warning("".join(traceback.format_exception(e)))


def parse_data_from_frontend(form_spec: FormSpec, field_id: str) -> Any:
    """Computes/validates the value from a vue formular field"""
    if not request.has_var(field_id):
        raise MKGeneralException("Formular data is missing in request")
    value_from_frontend = json.loads(request.get_str_input_mandatory(field_id))
    _schema, _vue_value, validation, data_for_disk = _visit(
        VisitorOptions(data_mode=DataOrigin.DISK, validate=True), form_spec, value_from_frontend
    )
    _process_validation_errors(validation)
    return data_for_disk
