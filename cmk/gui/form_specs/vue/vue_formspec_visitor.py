#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
import traceback
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from enum import auto, Enum
from typing import Any, Sequence, TypeVar

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private.definitions import LegacyValueSpec
from cmk.gui.form_specs.private.validators import IsFloat, IsInteger
from cmk.gui.form_specs.vue.type_defs.vue_formspec_components import (
    VueCascadingSingleChoice,
    VueCascadingSingleChoiceElement,
    VueDictionary,
    VueDictionaryElement,
    VueFloat,
    VueInteger,
    VueLegacyValuespec,
    VueList,
    VueSchema,
    VueSingleChoice,
    VueSingleChoiceElement,
    VueString,
)
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.rule_specs.legacy_converter import _convert_to_legacy_valuespec
from cmk.gui.utils.user_errors import user_errors

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DefaultValue,
    Dictionary,
    Float,
    FormSpec,
    InputHint,
    Integer,
    List,
    Percentage,
    SingleChoice,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError

ModelT = TypeVar("ModelT")


# TODO: find better solution for default value type
class DEFAULT_VALUE:
    pass


_default_value = DEFAULT_VALUE()


DataForDisk = Any
Value = Any


@dataclass(kw_only=True)
class Validation:
    location: list[str]
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


# DEBUG STUFF START #######################
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


# DEBUG STUFF END #######################


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


def _optional_validation(
    validators: Sequence[Callable[[ModelT], object]], raw_value: Any
) -> list[str]:
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


def _compute_validation_errors(
    visitor_options: VisitorOptions,
    validators: Sequence[Callable[[ModelT], object]],
    raw_value: Any,
) -> list[Validation]:
    if not visitor_options.validate:
        return []

    return [
        Validation(location=[""], message=x)
        for x in _optional_validation(validators, raw_value)
        if x is not None
    ]


def _visit_integer(
    visitor_options: VisitorOptions, form_spec: Integer, value: int | DEFAULT_VALUE
) -> VueVisitorMethodResult:
    if isinstance(value, DEFAULT_VALUE):
        value = form_spec.prefill.value

    title, help_text = _get_title_and_help(form_spec)

    validators = [IsInteger()] + (
        list(form_spec.custom_validate) if form_spec.custom_validate else []
    )

    result = (
        VueInteger(title=title, help=help_text, validators=build_vue_validators(validators)),
        value,
        _compute_validation_errors(visitor_options, validators, value),
        value,
    )
    return result


def _visit_float(
    visitor_options: VisitorOptions, form_spec: Float, value: float | DEFAULT_VALUE
) -> VueVisitorMethodResult:
    if isinstance(value, DEFAULT_VALUE):
        value = form_spec.prefill.value

    title, help_text = _get_title_and_help(form_spec)
    validators = [IsFloat()] + (
        list(form_spec.custom_validate) if form_spec.custom_validate else []
    )

    result = (
        VueFloat(title=title, help=help_text, validators=build_vue_validators(validators)),
        value,
        _compute_validation_errors(visitor_options, validators, value),
        value,
    )
    return result


def _visit_string(
    visitor_options: VisitorOptions, form_spec: String, value: str | DEFAULT_VALUE
) -> VueVisitorMethodResult:
    if isinstance(value, DEFAULT_VALUE):
        value = form_spec.prefill.value

    title, help_text = _get_title_and_help(form_spec)
    validators = form_spec.custom_validate if form_spec.custom_validate else []

    result = (
        VueString(title=title, help=help_text, validators=build_vue_validators(validators)),
        value,
        _compute_validation_errors(visitor_options, validators, value),
        value,
    )
    return result


def _visit_dictionary(
    visitor_options: VisitorOptions, form_spec: Dictionary, value: dict[str, Any] | DEFAULT_VALUE
) -> VueVisitorMethodResult:
    if isinstance(value, DEFAULT_VALUE):
        value = {}
    assert isinstance(value, dict)

    title, help_text = _get_title_and_help(form_spec)
    elements_keyspec = []
    vue_values = {}
    element_validations = []
    disk_values = {}

    for key_name, dict_element in form_spec.elements.items():
        is_active = key_name in value
        key_value = value[key_name] if is_active else _default_value

        element_schema, element_vue_value, element_vue_validation, element_disk_value = _visit(
            visitor_options, dict_element.parameter_form, key_value
        )

        for validation in element_vue_validation:
            element_validations.append(
                Validation(
                    location=[key_name] + validation.location,
                    message=validation.message,
                )
            )

        if is_active:
            disk_values[key_name] = element_disk_value
            vue_values[key_name] = key_value

        elements_keyspec.append(
            VueDictionaryElement(
                ident=key_name,
                default_value=element_vue_value,
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


def _visit_single_choice(
    visitor_options: VisitorOptions, form_spec: SingleChoice, value: str | DEFAULT_VALUE
) -> VueVisitorMethodResult:

    elements_to_show = []

    if isinstance(value, DEFAULT_VALUE):
        if isinstance(form_spec.prefill, InputHint):
            value = ""
            elements_to_show.append(
                VueSingleChoiceElement(
                    name="", title=form_spec.prefill.value.localize(translate_to_current_language)
                )
            )
        else:
            value = form_spec.prefill.value

    title, help_text = _get_title_and_help(form_spec)

    # TODO: add special __post_init__ / ignored_elements / invalid element
    #      validators for this form spec
    validators = form_spec.custom_validate if form_spec.custom_validate else []

    vue_elements: list[VueSingleChoiceElement] = []
    for element in form_spec.elements:
        vue_elements.append(
            VueSingleChoiceElement(
                name=element.name,
                title=element.title.localize(translate_to_current_language),
            )
        )

    result = (
        VueSingleChoice(
            title=title,
            help=help_text,
            elements=vue_elements,
            validators=build_vue_validators(validators),
        ),
        value,
        _compute_validation_errors(visitor_options, validators, value),
        value,
    )
    return result


def _visit_cascading_single_choice(
    visitor_options: VisitorOptions,
    form_spec: CascadingSingleChoice,
    value: tuple[str, Any] | DEFAULT_VALUE,
) -> VueVisitorMethodResult:

    selected_name = ""
    selected_value = _default_value

    elements_to_show = []
    if isinstance(value, DEFAULT_VALUE):
        if isinstance(form_spec.prefill, InputHint):
            elements_to_show.append(
                VueSingleChoiceElement(
                    name="", title=form_spec.prefill.value.localize(translate_to_current_language)
                )
            )
        else:
            assert isinstance(form_spec.prefill, DefaultValue)
            selected_name = form_spec.prefill.value
    else:
        selected_name = value[0]
        selected_value = value[1]

    title, help_text = _get_title_and_help(form_spec)

    # TODO: add special __post_init__ / element validators for this form spec
    validators = form_spec.custom_validate if form_spec.custom_validate else []

    selected_disk_value: Any = None
    vue_elements: list[VueCascadingSingleChoiceElement] = []
    element_validations = []
    for element in form_spec.elements:
        element_value = _default_value if selected_name != element.name else selected_value
        element_schema, element_vue_value, element_vue_validation, element_disk_value = _visit(
            visitor_options, element.parameter_form, element_value
        )
        if selected_name == element.name:
            selected_value = element_vue_value
            selected_disk_value = element_disk_value

        for validation in element_vue_validation:
            element_validations.append(
                Validation(
                    location=[element.name] + validation.location,
                    message=validation.message,
                )
            )

        vue_elements.append(
            VueCascadingSingleChoiceElement(
                name=element.name,
                title=element.title.localize(translate_to_current_language),
                default_value=element_vue_value,
                parameter_form=element_schema,
            )
        )

    result = (
        VueCascadingSingleChoice(
            title=title,
            help=help_text,
            elements=vue_elements,
            validators=build_vue_validators(validators),
        ),
        (selected_name, selected_value),
        element_validations,
        (selected_name, selected_disk_value),
    )
    return result


def _visit_list(
    visitor_options: VisitorOptions, form_spec: List, value: list | DEFAULT_VALUE
) -> VueVisitorMethodResult:

    if isinstance(value, DEFAULT_VALUE):
        value = []

    value = [2, 4, 6, 8]

    element_schema, element_vue_default_value, _element_vue_validation, _element_disk_value = (
        _visit(visitor_options, form_spec.element_template, _default_value)
    )
    title, help_text = _get_title_and_help(form_spec)

    vue_values = []
    disk_values = []
    element_validations = []
    for idx, element_value in enumerate(value):
        element_schema, element_vue_value, element_vue_validation, element_disk_value = _visit(
            visitor_options, form_spec.element_template, element_value
        )
        vue_values.append(element_vue_value)
        disk_values.append(element_disk_value)
        for validation in element_vue_validation:
            element_validations.append(
                Validation(
                    location=[str(idx)] + validation.location,
                    message=validation.message,
                )
            )

    return (
        VueList(
            title=title,
            help=help_text,
            element_template=element_schema,
            element_default_value=element_vue_default_value,
            add_element_label=form_spec.add_element_label.localize(translate_to_current_language),
            remove_element_label=form_spec.remove_element_label.localize(
                translate_to_current_language
            ),
            no_element_label=form_spec.no_element_label.localize(translate_to_current_language),
        ),
        vue_values,
        element_validations,
        disk_values,
    )


def _visit_legacyvaluespec(
    _visitor_options: VisitorOptions, form_spec: LegacyValueSpec, value: Any
) -> VueVisitorMethodResult:
    """
    The legacy valuespec requires a special handling to compute the actual value
    If the value contains the key 'input_context' it comes from the frontend form.
    This requires the value to be evaluated with the legacy valuespec and the varprefix system.
    """

    if isinstance(value, DEFAULT_VALUE):
        value = form_spec.valuespec.default_value()

    title, help_text = _get_title_and_help(form_spec)

    config: dict[str, Any] = {}
    if isinstance(value, dict) and "input_context" in value:
        with request.stashed_vars():
            varprefix = value.get("varprefix", "")
            for url_key, url_value in value.get("input_context", {}).items():
                request.set_var(url_key, url_value)

            try:
                value = form_spec.valuespec.from_html_vars(varprefix)
                form_spec.valuespec.validate_datatype(value, varprefix)
                form_spec.valuespec.validate_value(value, varprefix)
            except MKUserError as e:
                user_errors.add(e)
                validation_errors = [Validation(location=[""], message=str(e))]
                with output_funnel.plugged():
                    # Keep in mind that this default value is actually not used,
                    # but replaced by the request vars
                    form_spec.valuespec.render_input(varprefix, form_spec.valuespec.default_value())
                    return (
                        VueLegacyValuespec(
                            title=title,
                            help=help_text,
                            html=output_funnel.drain(),
                            varprefix=varprefix,
                        ),
                        None,
                        validation_errors,
                        value,
                    )

    varprefix = f"legacy_varprefix_{uuid.uuid4()}"
    with output_funnel.plugged():
        validation_errors = []
        try:
            form_spec.valuespec.render_input(varprefix, value)
        except MKUserError as e:
            validation_errors = [Validation(location=[""], message=str(e))]
        return (
            VueLegacyValuespec(
                title=title,
                help=help_text,
                html=output_funnel.drain(),
                varprefix=varprefix,
            ),
            config,
            validation_errors,
            value,
        )


_form_specs_visitor_registry: dict[type, VueFormSpecVisitorMethod] = {}


def register_class(validator_class: type, visitor_function: VueFormSpecVisitorMethod) -> None:
    _form_specs_visitor_registry[validator_class] = visitor_function


def register_form_specs():
    # TODO: add test which checks if all available FormSpecs have a visitor
    register_class(Integer, _visit_integer)
    register_class(Dictionary, _visit_dictionary)
    register_class(String, _visit_string)
    register_class(Float, _visit_float)
    register_class(SingleChoice, _visit_single_choice)
    register_class(CascadingSingleChoice, _visit_cascading_single_choice)
    register_class(List, _visit_list)
    register_class(LegacyValueSpec, _visit_legacyvaluespec)


register_form_specs()

# Vue is able to render these types in the frontend directly
NativeVueFormSpecTypes = (
    Integer
    | Float
    | String
    | SingleChoice
    | CascadingSingleChoice
    | Dictionary
    | List
    | LegacyValueSpec
)

ConvertableVueFormSpecTypes = Percentage


def _convert_to_supported_form_spec(custom_form_spec: FormSpec) -> NativeVueFormSpecTypes:
    # TODO: switch to match statement
    if isinstance(custom_form_spec, NativeVueFormSpecTypes):  # type: ignore[misc, arg-type]
        # This FormSpec type can be rendered by vue natively
        return custom_form_spec  # type: ignore[return-value]

    try:
        # Convert custom_form_spec to valuespec and feed it to LegacyValueSpec
        valuespec = _convert_to_legacy_valuespec(custom_form_spec, translate_to_current_language)
        return LegacyValueSpec(
            title=Title(  # pylint: disable=localization-of-non-literal-string
                str(valuespec.title() or "")
            ),
            help_text=Help(  # pylint: disable=localization-of-non-literal-string
                str(valuespec.help() or "")
            ),
            valuespec=valuespec,
        )
    except Exception:
        pass

    # Raise an error if the custom_form_spec is not supported
    raise MKUserError("", f"UNKNOWN/unconvertable custom_form_spec {custom_form_spec}")


def _convert_to_native_form_spec(
    custom_form_spec: ConvertableVueFormSpecTypes,
) -> NativeVueFormSpecTypes:
    if isinstance(custom_form_spec, Percentage):
        return Float(
            title=custom_form_spec.title,
            help_text=custom_form_spec.help_text,
            label=custom_form_spec.label,
            prefill=custom_form_spec.prefill,
            unit_symbol="%",
        )
    raise MKUserError("", f"Unsupported native conversion for {custom_form_spec}")


def _process_validation_errors(validation_errors: list[Validation]) -> None:
    """This functions introduces validation errors from the vue-world into the CheckMK-GUI-world
    The CheckMK-GUI works with a global parameter user_errors.
    These user_errors include the field_id of the broken input field and the error text
    """
    # TODO: this function will become obsolete once all errors are shown within the form spec
    if not validation_errors:
        return

    ## Our current error handling can only show one error at a time in the red error box.
    ## This is just a quickfix
    # for error in validation_errors[1:]:
    #    user_errors.add(MKUserError("", error.message))

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
        logger.warning("Vue app config:\n%s", pprint.pformat(vue_app_config, width=220))
        logger.warning("Vue value:\n%s", pprint.pformat(vue_value, width=220))
        logger.warning("Vue validation:\n%s", pprint.pformat(validation, width=220))
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
