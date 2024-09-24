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
from cmk.gui.validation.visitors.vue_lib import (
    ValidationError,
    VueAppConfig,
    VueFormSpecComponent,
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

VueVisitorMethodResult = tuple[VueFormSpecComponent, Any]
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
    _vue_config: VueFormSpecComponent
    _raw_value: Any

    def __init__(self, form_spec: FormSpec, value: Any, do_validate: bool = True):
        self._do_validate = do_validate
        self._aggregated_validation_errors = set[ValidationError]()
        self._vue_config, self._raw_value = self._visit(form_spec, value)

    @property
    def vue_config(self):
        return self._vue_config

    @property
    def raw_value(self):
        return self._raw_value

    @property
    def validation_errors(self) -> set[ValidationError]:
        return self._aggregated_validation_errors

    def _component_to_dict(self, component: VueFormSpecComponent) -> dict[str, Any]:
        return asdict(component)

    @final
    def _visit(self, form_spec: FormSpec, value: Any) -> tuple[VueFormSpecComponent, Any]:
        basic_form_spec = _convert_to_supported_form_spec(form_spec)

        with _change_log_indent(2):
            visitor: VueFormSpecVisitorMethod = self._get_matching_visit_function(basic_form_spec)
            _log_indent(f"-> visiting {basic_form_spec.__class__.__name__} {value}")
            component_result, raw_value = visitor(basic_form_spec, value)
            self._handle_validation(basic_form_spec, component_result, raw_value)

        return component_result, raw_value

    def _get_matching_visit_function(self, form_spec: FormSpec) -> VueFormSpecVisitorMethod:
        _log_indent(f"find visitor for {form_spec}")
        # TODO: match/case
        if isinstance(form_spec, Integer):
            return self._visit_integer
        if isinstance(form_spec, Float):
            return self._visit_float
        if isinstance(form_spec, Percentage):
            return self._visit_percentage
        if isinstance(form_spec, Dictionary):
            return self._visit_dictionary
        if isinstance(form_spec, CascadingSingleChoice):
            return self._visit_cascading_dropdown
        if isinstance(form_spec, SingleChoice):
            return self._visit_dropdown_choice
        if isinstance(form_spec, List):
            return self._visit_list
        if isinstance(form_spec, String):
            return self._visit_text
        raise MKGeneralException(f"No visitor for {form_spec}")

    def _handle_validation(
        self, node: FormSpec, component_result: VueFormSpecComponent, raw_value: Any
    ) -> None:
        # TODO: rework validation to support FormSpec
        with _change_log_indent(4):
            if self._do_validate:
                _log_indent(f"  validate {node.__class__.__name__}")
                try:
                    custom_validate = node.custom_validate  # type: ignore[attr-defined]
                except Exception:
                    # Basic exception handling -> TODO: inspect, etc.
                    # Not every formspec has a custom validate callable
                    _log_indent(f"  no custom validate for {node.__class__.__name__}")
                    return

                try:
                    if custom_validate is not None:
                        _ = [custom_val(raw_value) for custom_val in custom_validate]

                except MKUserError as e:
                    error = ValidationError(message=str(e), field_id=e.varname or str(uuid.uuid4()))
                    component_result.validation_errors = [error.message]
                    # The aggregated errors are used within our old GUI which
                    # requires the MKUser error format (field_id + message)
                    self._aggregated_validation_errors.add(error)

    def _visit_integer(self, form_spec: Integer, value: int) -> VueVisitorMethodResult:
        return (
            VueFormSpecComponent(
                form_spec,
                component_type="integer",
                config={
                    "value": 0 if value is None else value,
                    "label": form_spec.title.localize(_) if form_spec.title else None,
                    "unit": form_spec.unit_symbol if form_spec.unit_symbol else None,
                },
            ),
            value,
        )

    def _visit_float(self, form_spec: Float, value: float) -> VueVisitorMethodResult:
        return (
            VueFormSpecComponent(
                form_spec,
                component_type="float",
                config={
                    "value": 0 if value is None else value,
                    "label": form_spec.title.localize(_) if form_spec.title else None,
                    "unit": form_spec.unit_symbol if form_spec.unit_symbol else None,
                },
            ),
            value,
        )

    def _visit_percentage(
        self, form_spec: Percentage, value: int | float
    ) -> VueVisitorMethodResult:
        return (
            VueFormSpecComponent(
                form_spec,
                component_type="percentage",
                config={
                    "value": value,
                    "label": form_spec.label.localize(_) if form_spec.label else None,
                    # FIXME
                    # Sorry, 20 looks awful. Legacy value specs use "%r" now.
                    # That is better behaved with respect to undesired cut-off effects.
                    "precision": 20,
                },
            ),
            value,
        )

    def _visit_dictionary(
        self, form_spec: Dictionary, value: dict[str, Any]
    ) -> VueVisitorMethodResult:
        dict_elements = []
        raw_value = {}
        for key_name, dict_element in form_spec.elements.items():
            is_active = key_name in value
            key_value = (
                value[key_name] if is_active else compute_default_value(dict_element.parameter_form)
            )

            component_result, component_value = self._visit(dict_element.parameter_form, key_value)
            if is_active:
                raw_value[key_name] = component_value
            dict_elements.append(
                {
                    "name": key_name,
                    "required": dict_element.required,
                    "is_active": is_active,
                    "component": self._component_to_dict(component_result),
                }
            )

        return (
            VueFormSpecComponent(
                form_spec,
                component_type="dictionary",
                config={"elements": dict_elements},
            ),
            raw_value,
        )

    def _visit_cascading_dropdown(
        self, form_spec: CascadingSingleChoice, value: tuple[str, Any] | None
    ) -> VueVisitorMethodResult:
        elements = []

        if value is None:
            value = compute_default_value(form_spec)

        for element in form_spec.elements:
            if value[0] == element.name:
                used_value = value[1]
            else:
                used_value = compute_default_value(element.parameter_form)

            form_title = element.parameter_form.title
            cascading_title = form_title.localize(_) if form_title else element.name
            choice_component, _choice_raw_value = self._visit(element.parameter_form, used_value)
            elements.append(
                (
                    element.name,
                    cascading_title,
                    choice_component,
                )
            )

        return (
            VueFormSpecComponent(
                form_spec,
                component_type="cascading_dropdown_choice",
                config={
                    "elements": elements,
                    "value": value,
                },
            ),
            value,
        )

    def _visit_dropdown_choice(self, form_spec: SingleChoice, value: Any) -> VueVisitorMethodResult:
        # TODO: improve transform. the frontend only renders strings
        return (
            VueFormSpecComponent(
                form_spec,
                component_type="dropdown_choice",
                config={
                    "elements": list(
                        [str(x.name), x.title.localize(_)] for x in form_spec.elements
                    ),
                    "value": str(value),
                },
            ),
            value,
        )

    def _visit_list(self, form_spec: List, value: list) -> VueVisitorMethodResult:
        template, _ = self._visit(
            form_spec.element_template,
            compute_default_value(form_spec.element_template),
        )

        elements = []
        raw_value = []
        for element in value:
            component, element_raw_value = self._visit(form_spec.element_template, element)
            elements.append(component)
            raw_value.append(element_raw_value)

        return (
            VueFormSpecComponent(
                form_spec,
                component_type="list_of",
                config={
                    "template": template,
                    "add_text": _("Add new element"),
                    "elements": elements,
                },
            ),
            raw_value,
        )

    def _visit_text(self, form_spec: String, value: str) -> VueVisitorMethodResult:
        return (
            VueFormSpecComponent(
                form_spec,
                component_type="text",
                config={
                    "value": "" if value is None else value,
                },
            ),
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
    return String(title=Title("UNKNOWN custom_form_spec {custom_form_spec}"))


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
    _log_indent("VISITOR RAW VALUE %s" % pprint.pformat(vue_visitor.raw_value))
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
        VueAppConfig(id=app_id, app_name="demo", component=asdict(vue_visitor.vue_config))
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
    _log_indent("%s" % pprint.pformat(vue_app_config, width=180))
    html.div("", data_cmk_vue_app=json.dumps(vue_app_config))


def parse_and_validate_form_spec(form_spec: FormSpec, field_id: str) -> Any:
    """Computes/validates the value from a vue formular field"""
    if not request.has_var(field_id):
        raise MKGeneralException("Formular data is missing in request")
    value_from_frontend = json.loads(request.get_str_input_mandatory(field_id))
    vue_visitor = create_form_spec_visitor(form_spec, value_from_frontend, do_validate=True)
    _process_validation_errors(vue_visitor)
    return vue_visitor.raw_value
