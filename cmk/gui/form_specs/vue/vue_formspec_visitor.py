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
from typing import Any, final

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
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec.to_formspec import ValueSpecFormSpec

from cmk.rulesets.v1 import Message, Title
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

# TODO: improve typing
DataForDisk = Any
Value = Any


@dataclass(kw_only=True)
class Validation:
    location: list
    message: str


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    form_spec: dict[str, Any]
    model_value: Any
    validation_messages: Any


VueVisitorMethodResult = tuple[VueSchema, Value, list[Validation], DataForDisk]
VueFormSpecVisitorMethod = Callable[[Any, Any], VueVisitorMethodResult]


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


class DataOrigin(Enum):
    DISK = auto()
    FRONTEND = auto()


class AbstractFormSpecVisitor:
    """Tasks
    - vue schema creation
    - compute value
    - validate value"""

    _do_validate: bool
    _vue_schema: VueSchema
    _vue_value: Value
    _vue_validation: list[Validation]
    _data_for_disk: DataForDisk

    def __init__(
        self, form_spec: FormSpec, value: Any, data_mode: DataOrigin, do_validate: bool = True
    ):
        self._do_validate = do_validate
        self._input_data_mode = data_mode
        self._aggregated_validation_errors = set[Message]()
        self._vue_schema, self._vue_value, self._vue_validation, self._data_for_disk = self._visit(
            form_spec, value
        )

    @property
    def vue_schema(self):
        return self._vue_schema

    @property
    def validation(self):
        return self._vue_validation

    @property
    def value(self):
        return self._vue_value

    @property
    def data_for_disk(self) -> Any:
        if self._aggregated_validation_errors:
            raise MKUserError(
                "", _("Validation errors occurred. Please fix the input fields and try again.")
            )
        return self._data_for_disk

    @property
    def validation_errors(self) -> set[Message]:
        return self._aggregated_validation_errors

    def _schema_to_dict(self, component: VueSchema) -> dict[str, Any]:
        return asdict(component)

    @final
    def _visit(self, form_spec: FormSpec, value: Any) -> VueVisitorMethodResult:
        basic_form_spec = _convert_to_supported_form_spec(form_spec)

        visitor: VueFormSpecVisitorMethod = self._get_matching_visit_function(basic_form_spec)
        if self._input_data_mode == DataOrigin.DISK and basic_form_spec.migrate:
            value = basic_form_spec.migrate(value)
        return visitor(basic_form_spec, value)

    def _get_matching_visit_function(self, form_spec: FormSpec) -> VueFormSpecVisitorMethod:
        # TODO: match/case
        if isinstance(form_spec, Integer):
            return self._visit_integer
        #        if isinstance(form_spec, Float):
        #            return self._visit_float
        if isinstance(form_spec, Dictionary):
            return self._visit_dictionary
        #        if isinstance(form_spec, List):
        #            return self._visit_list
        #        if isinstance(form_spec, String):
        #            return self._visit_text
        #        if isinstance(form_spec, ValueSpecFormSpec):
        #            return self._visit_legacy_valuespec
        raise MKGeneralException(f"No visitor for {form_spec}")

    def _optional_validation(self, form_spec: FormSpec, raw_value: Any) -> list[str]:
        validation_errors = []
        if self._do_validate:
            if form_spec.custom_validate is not None:
                for custom_val in form_spec.custom_validate:
                    try:
                        raw_value = custom_val(raw_value)
                    except ValidationError as e:
                        validation_errors.append(e.message.localize(translate_to_current_language))
                        # The aggregated errors are used within our old GUI which
                        # requires the MKUser error format (field_id + message)
                        # self._aggregated_validation_errors.add(e.message)
                        # TODO: add external validation errors for legacy formspecs
                        #       or handle it within the form_spec_valuespec_wrapper
        return validation_errors

    def _get_title_and_help(self, form_spec: FormSpec) -> tuple[str, str]:
        title = (
            ""
            if form_spec.title is None
            else form_spec.title.localize(translate_to_current_language)
        )
        help_text = (
            ""
            if form_spec.help_text is None
            else form_spec.help_text.localize(translate_to_current_language)
        )
        return title, help_text

    def _visit_integer(self, form_spec: Integer, value: int) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        custom_validators = (
            [IsInteger()] + list(form_spec.custom_validate) if form_spec.custom_validate else []
        )

        result = (
            VueInteger(
                title=title, help=help_text, validators=build_vue_validators(custom_validators)
            ),
            value,
            list(
                Validation(location=[""], message=x)
                for x in self._optional_validation(form_spec, value)
                if x is not None
            ),
            value,
        )
        return result

    #    def _visit_float(self, form_spec: Float, value: float) -> VueVisitorMethodResult:
    #        title, help_text = self._get_title_and_help(form_spec)
    #        result = (
    #            VueFloat(
    #                title=title,
    #                help=help_text,
    #                validators=build_vue_validators(form_spec.custom_validate)
    #            ),
    #            self._compute_value_and_validation(form_spec, value, value),
    #            value,
    #        )
    #        return result

    def _visit_dictionary(
        self, form_spec: Dictionary, value: dict[str, Any]
    ) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        elements_keyspec = []
        vue_values = {}
        element_validations = []
        disk_values = {}

        for key_name, dict_element in form_spec.elements.items():
            is_active = key_name in value
            key_value = (
                value[key_name]
                if is_active
                else _compute_default_value(dict_element.parameter_form)
            )

            element_schema, vue_value, vue_validation, disk_value = self._visit(
                dict_element.parameter_form, key_value
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


#    def _visit_list(self, form_spec: List, value: list) -> VueVisitorMethodResult:
#        title, help_text = self._get_title_and_help(form_spec)
#        vue_schema, _value, _data_for_disk = self._visit(
#            form_spec.element_template, _compute_default_value(form_spec.element_template)
#        )
#
#        elements = []
#        vue_values = []
#        disk_values = []
#        for element in value:
#            component, vue_value, disk_value = self._visit(form_spec.element_template, element)
#            elements.append(component)
#            vue_values.append(vue_value)
#            disk_values.append(disk_value)
#
#        return (
#            VueList(title=title, help=help_text, vue_schema=vue_schema),
#            self._compute_value_and_validation(form_spec, vue_values, disk_values),
#            disk_values,
#        )
#
#    def _visit_text(self, form_spec: String, value: str) -> VueVisitorMethodResult:
#        title, help_text = self._get_title_and_help(form_spec)
#        return (
#            VueText(
#                title=title,
#                help=help_text,
#            ),
#            self._compute_value_and_validation(form_spec, value, value),
#            value,
#        )
#
#    def _visit_legacy_valuespec(
#        self, form_spec: ValueSpecFormSpec, value: Any
#    ) -> VueVisitorMethodResult:
#        """
#        The legacy valuespec requires a special handling to compute the actual value
#        If the value contains the key 'input_context' it comes from the frontend form.
#        This requires the value to be evaluated with the legacy valuespec and the varprefix system.
#        """
#
#        vue_value: dict[str, Any] = {}
#        legacy_valuespec = form_spec.valuespec
#        if self._input_data_mode == InputDataMode.DATA_FROM_FRONTEND:
#            input_context = value.get("input_context")
#            with request.stashed_vars():
#                varprefix = value.get("varprefix", "")
#                for url_key, url_value in input_context.items():
#                    request.set_var(url_key, url_value)
#
#                try:
#                    disk_value = legacy_valuespec.from_html_vars(varprefix)
#                    legacy_valuespec.validate_datatype(disk_value, varprefix)
#                    legacy_valuespec.validate_value(disk_value, varprefix)
#                except MKUserError as e:
#                    disk_value = None  # Broken value
#                    with output_funnel.plugged():
#                        # Keep in mind that this default value is actually not used,
#                        # but replaced by the request vars
#                        legacy_valuespec.render_input(varprefix, legacy_valuespec.default_value())
#                        vue_value["html"] = output_funnel.drain()
#                        vue_value["varprefix"] = varprefix
#                    return (
#                        VueLegacyValuespec(
#                            title="",
#                            help="",
#                        ),
#                        ValueAndValidation(vue_value, str(e)),
#                        disk_value,
#                    )
#        else:  # DATA_FROM_DISK
#            disk_value = value
#
#        varprefix = f"legacy_varprefix_{uuid.uuid4()}"
#        with output_funnel.plugged():
#            legacy_valuespec.render_input(varprefix, disk_value)
#            vue_value["html"] = output_funnel.drain()
#            vue_value["varprefix"] = varprefix
#
#        return (
#            VueLegacyValuespec(
#                title="",
#                help="",
#            ),
#            ValueAndValidation(vue_value, ""),
#            disk_value,
#        )


class _FormDataFromDisk(AbstractFormSpecVisitor):
    def __init__(self, form_spec: FormSpec, value: Any, do_validate: bool = True):
        super().__init__(form_spec, value, DataOrigin.DISK, do_validate=do_validate)


class _FormDataFromFrontend(AbstractFormSpecVisitor):
    def __init__(self, form_spec: FormSpec, value: Any, do_validate: bool = True):
        super().__init__(form_spec, value, DataOrigin.FRONTEND, do_validate=do_validate)


# Vue is able to render these types in the frontend
VueFormSpecTypes = (
    Integer
    | Float
    | Percentage
    | String
    | SingleChoice
    | CascadingSingleChoice
    | Dictionary
    | List
    | ValueSpecFormSpec
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


def _process_validation_errors(vue_visitor: AbstractFormSpecVisitor) -> None:
    """This functions introduces validation errors from the vue-world into the CheckMK-GUI-world
    The CheckMK-GUI works with a global parameter user_errors.
    These user_errors include the field_id of the broken input field and the error text
    """
    # TODO: this function will become obsolete once all errors are shown within the form spec
    if validation_errors := list(vue_visitor.validation_errors):
        # Our current error handling can only show one error at a time in the red error box.
        # This is just a quickfix
        for validation_error in validation_errors[1:]:
            user_errors.add(
                MKUserError("", validation_error.localize(translate_to_current_language))
            )

        first_error = validation_errors[0]
        raise MKUserError("", first_error.localize(translate_to_current_language))


def _create_form_spec_app_config(
    vue_visitor: AbstractFormSpecVisitor, app_id: str
) -> dict[str, Any]:
    # logger.warning(f"Vue app config:\n{pprint.pformat(vue_visitor.vue_schema, width=220)}")
    # logger.warning(f"Vue value:\n{pprint.pformat(vue_visitor.value, width=220)}")
    # logger.warning(f"Disk value:\n{pprint.pformat(vue_visitor.data_for_disk, width=220)}")
    return asdict(
        VueAppConfig(
            id=app_id,
            app_name="form_spec",
            form_spec=asdict(vue_visitor.vue_schema),
            model_value=vue_visitor.value,
            validation_messages=vue_visitor.validation,
        )
    )


def render_form_spec(form_spec: FormSpec, field_id: str, default_value: Any) -> None:
    """Renders the valuespec via vue within a div"""
    if request.has_var(field_id):
        value = json.loads(request.get_str_input_mandatory(field_id))
        do_validate = True
    else:
        value = default_value
        do_validate = False

    try:
        vue_visitor = _FormDataFromDisk(form_spec, value, do_validate=do_validate)
        vue_app_config = _create_form_spec_app_config(vue_visitor, field_id)
        logger.warning(pprint.pformat(vue_app_config))
        html.div("", data_cmk_vue_app=json.dumps(vue_app_config))
    except Exception as e:
        logger.warning("".join(traceback.format_exception(e)))


def parse_data_from_frontend(form_spec: FormSpec, field_id: str) -> Any:
    """Computes/validates the value from a vue formular field"""
    if not request.has_var(field_id):
        raise MKGeneralException("Formular data is missing in request")
    value_from_frontend = json.loads(request.get_str_input_mandatory(field_id))
    vue_visitor = _FormDataFromFrontend(form_spec, value_from_frontend, do_validate=True)
    _process_validation_errors(vue_visitor)
    return vue_visitor.data_for_disk
