#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pprint
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any, Callable, final

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.validation.visitors.vue_lib import ValidationError, ValueAndValidation, VueAppConfig
from cmk.gui.validation.visitors.vue_types import (
    VueDictionary,
    VueDictionaryElement,
    VueFloat,
    VueInteger,
    VueList,
    VueSchema,
    VueText,
)

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

DataForDisk = Any
VueVisitorMethodResult = tuple[VueSchema, ValueAndValidation, DataForDisk]
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


class VueFormSpecVisitor:
    """Tasks
    - vue schema creation
    - compute value
    - validate value"""

    _do_validate: bool
    _vue_schema: VueSchema
    _vue_value: ValueAndValidation
    _data_for_disk: DataForDisk

    def __init__(self, form_spec: FormSpec, value: Any, do_validate: bool = True):
        self._do_validate = do_validate
        self._aggregated_validation_errors = set[ValidationError]()
        self._vue_schema, self._vue_value, self._data_for_disk = self._visit(form_spec, value)

    @property
    def vue_schema(self):
        return self._vue_schema

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
    def validation_errors(self) -> set[ValidationError]:
        return self._aggregated_validation_errors

    def _schema_to_dict(self, component: VueSchema) -> dict[str, Any]:
        return asdict(component)

    @final
    def _visit(self, form_spec: FormSpec, value: Any) -> VueVisitorMethodResult:
        basic_form_spec = _convert_to_supported_form_spec(form_spec)

        with _change_log_indent(2):
            visitor: VueFormSpecVisitorMethod = self._get_matching_visit_function(basic_form_spec)
            _log_indent(f"-> visiting {basic_form_spec.__class__.__name__} {value}")
            return visitor(basic_form_spec, value)

    def _get_matching_visit_function(self, form_spec: FormSpec) -> VueFormSpecVisitorMethod:
        # _log_indent(f"find visitor for {form_spec}")
        # TODO: match/case
        if isinstance(form_spec, Integer):
            return self._visit_integer
        if isinstance(form_spec, Float):
            return self._visit_float
        if isinstance(form_spec, Dictionary):
            return self._visit_dictionary
        if isinstance(form_spec, List):
            return self._visit_list
        if isinstance(form_spec, String):
            return self._visit_text
        raise MKGeneralException(f"No visitor for {form_spec}")

    def _optional_validation(self, node: FormSpec, raw_value: Any) -> None | str:
        with _change_log_indent(4):
            if self._do_validate:
                _log_indent(f"  validate {node.__class__.__name__}")
                try:
                    custom_validate = node.custom_validate  # type: ignore[attr-defined]
                except Exception:
                    # Basic exception handling -> TODO: inspect, etc.
                    # Not every formspec has a custom validate callable
                    _log_indent(f"  no custom validate for {node.__class__.__name__}")
                    return None

                try:
                    if custom_validate is not None:
                        custom_validate(raw_value)
                except MKUserError as e:
                    error = ValidationError(message=str(e), field_id=e.varname or str(uuid.uuid4()))
                    # The aggregated errors are used within our old GUI which
                    # requires the MKUser error format (field_id + message)
                    self._aggregated_validation_errors.add(error)
                    return error.message
        return None

    def _compute_value_and_validation(
        self, form_spec: FormSpec, vue_value: Any, disk_value: Any
    ) -> ValueAndValidation:
        return ValueAndValidation(vue_value, self._optional_validation(form_spec, disk_value))

    def _get_title_and_help(self, form_spec: FormSpec) -> tuple[str, str]:
        title = "" if form_spec.title is None else form_spec.title.localize(_)
        help_text = "" if form_spec.help_text is None else form_spec.help_text.localize(_)
        return title, help_text

    def _visit_integer(self, form_spec: Integer, value: int) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        result = (
            VueInteger(
                title=title,
                help=help_text,
            ),
            self._compute_value_and_validation(form_spec, value, value),
            value,
        )
        return result

    def _visit_float(self, form_spec: Float, value: float) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        result = (
            VueFloat(
                title=title,
                help=help_text,
            ),
            self._compute_value_and_validation(form_spec, value, value),
            value,
        )
        return result

    def _visit_dictionary(
        self, form_spec: Dictionary, value: dict[str, Any]
    ) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        elements_keyspec = []
        vue_values = {}
        disk_values = {}

        for key_name, dict_element in form_spec.elements.items():
            is_active = key_name in value
            key_value = (
                value[key_name] if is_active else compute_default_value(dict_element.parameter_form)
            )

            element_schema, vue_value, disk_value = self._visit(
                dict_element.parameter_form, key_value
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
            self._compute_value_and_validation(form_spec, vue_values, disk_values),
            disk_values,
        )

    def _visit_list(self, form_spec: List, value: list) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        vue_schema, _value, _data_for_disk = self._visit(
            form_spec.element_template, compute_default_value(form_spec.element_template)
        )

        elements = []
        vue_values = []
        disk_values = []
        for element in value:
            component, vue_value, disk_value = self._visit(form_spec.element_template, element)
            elements.append(component)
            vue_values.append(vue_value)
            disk_values.append(disk_value)

        return (
            VueList(title=title, help=help_text, vue_schema=vue_schema),
            self._compute_value_and_validation(form_spec, vue_values, disk_values),
            disk_values,
        )

    def _visit_text(self, form_spec: String, value: str) -> VueVisitorMethodResult:
        title, help_text = self._get_title_and_help(form_spec)
        return (
            VueText(
                title=title,
                help=help_text,
            ),
            self._compute_value_and_validation(form_spec, value, value),
            value,
        )


# INFO: kept as reference for migration to FormSpec
#    def visit_legacyvaluespec(
#        self, node: elements.LegacyValueSpecElement, value: Any
#    ) -> VueVisitorMethodResult:
#        """
#        The legacy valuespec requires a special handling to compute the actual value
#        If the value contains the key 'input_context' it comes from the frontend form.
#        This requires the value to be evaluated with the legacy valuespec and the varprefix system.
#        """
#        config: dict[str, Any] = {}
#        if isinstance(value, dict) and "input_context" in value:
#            with request.stashed_vars():
#                varprefix = value.get("varprefix", "")
#                for url_key, url_value in value.get("input_context", {}).items():
#                    request.set_var(url_key, url_value)
#
#                try:
#                    value = node.details.valuespec.from_html_vars(varprefix)
#                    node.details.valuespec.validate_datatype(value, varprefix)
#                    node.details.valuespec.validate_value(value, varprefix)
#                except MKUserError as e:
#                    config["validation_errors"] = [str(e)]
#                    with output_funnel.plugged():
#                        # Keep in mind that this default value is actually not used,
#                        # but replaced by the request vars
#                        node.details.valuespec.render_input(
#                            varprefix, node.details.valuespec.default_value()
#                        )
#                        config["html"] = output_funnel.drain()
#                        config["varprefix"] = varprefix
#                    return (
#                        GenericComponent(node, component_type="legacy_valuespec", config=config),
#                        value,
#                    )
#
#        varprefix = f"legacy_varprefix_{uuid.uuid4()}"
#        with output_funnel.plugged():
#            node.details.valuespec.render_input(varprefix, value)
#            config["html"] = output_funnel.drain()
#            config["varprefix"] = varprefix
#
#        return GenericComponent(node, component_type="legacy_valuespec", config=config), value


# Vue is able to render these types in the frontend
VueFormSpecTypes = (
    Integer | Float | Percentage | String | SingleChoice | CascadingSingleChoice | Dictionary | List
)


def _convert_to_supported_form_spec(custom_form_spec: FormSpec) -> VueFormSpecTypes:
    # TODO: broken typing
    if isinstance(custom_form_spec, VueFormSpecTypes):  # type: ignore[misc, arg-type]
        # These FormSpec types can be rendered by vue natively
        return custom_form_spec  # type: ignore[return-value]

    # All other types require a conversion to the basic types
    if isinstance(custom_form_spec, ServiceState):
        # TODO handle ServiceState
        String(title=Title("UNKNOWN custom_form_spec ServiceState"))

    # If no explicit conversion exist, create an ugly valuespec
    # TODO: raise an exception
    return String(title=Title(f"UNKNOWN custom_form_spec {custom_form_spec}"))


def compute_default_value(form_spec: FormSpec) -> Any:
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


def create_form_spec_visitor(
    form_spec: FormSpec, value: Any, do_validate: bool = True
) -> VueFormSpecVisitor:
    _log_indent("CREATE FORM SPEC VISITOR %s" % pprint.pformat(value))
    vue_visitor = VueFormSpecVisitor(form_spec, value, do_validate=do_validate)
    # _log_indent(
    #     "VISITOR RAW VALUE %s" % pprint.pformat(vue_visitor.value_and_validation, width=220)
    # )
    return vue_visitor


def _process_validation_errors(vue_visitor: VueFormSpecVisitor) -> None:
    """This functions introduces validation errors from the vue-world into the CheckMK-GUI-world
    The CheckMK-GUI works with a global parameter user_errors.
    These user_errors include the field_id of the broken input field and the error text
    """
    if validation_errors := list(vue_visitor.validation_errors):
        # Our current error handling can only show one error at a time in the red error box.
        # This is just a quickfix
        for validation_error in validation_errors[1:]:
            user_errors.add(MKUserError(validation_error.field_id, validation_error.message))

        first_error = validation_errors[0]
        raise MKUserError(first_error.field_id, first_error.message)


def create_form_spec_app_config(vue_visitor: VueFormSpecVisitor, app_id: str) -> dict[str, Any]:
    return asdict(
        VueAppConfig(
            id=app_id,
            app_name="demo",
            vue_schema=asdict(vue_visitor.vue_schema),
            data=vue_visitor.value,
        )
    )


def render_form_spec(form_spec: FormSpec, field_id: str, default_value: Any) -> None:
    """Renders the valuespec via vue within a div
    The value to be rendered
    - might be taken from the request, which also enables validation
    - might be the default value, which is not validated since some mandatory fields might be empty
    """
    _log_indent("RENDER APP CONFIG")
    if request.has_var(field_id):
        value = json.loads(request.get_str_input_mandatory(field_id))
        do_validate = True
    else:
        value = default_value
        do_validate = False

    vue_visitor = create_form_spec_visitor(form_spec, value, do_validate=do_validate)
    vue_app_config = create_form_spec_app_config(vue_visitor, field_id)
    # logger.warning(f"Vue app config:\n{pprint.pformat(vue_app_config, width=220)}")
    # logger.warning(f"Vue value:\n{pprint.pformat(vue_visitor.value, width=220)}")
    # logger.warning(f"Disk value:\n{pprint.pformat(vue_visitor.data_for_disk, width=220)}")
    html.div("", data_cmk_vue_app=json.dumps(vue_app_config))


def parse_and_validate_form_spec(form_spec: FormSpec, field_id: str) -> Any:
    """Computes/validates the value from a vue formular field"""
    if not request.has_var(field_id):
        raise MKGeneralException("Formular data is missing in request")
    value_from_frontend = json.loads(request.get_str_input_mandatory(field_id))
    vue_visitor = create_form_spec_visitor(form_spec, value_from_frontend, do_validate=True)
    _process_validation_errors(vue_visitor)
    return vue_visitor.data_for_disk
