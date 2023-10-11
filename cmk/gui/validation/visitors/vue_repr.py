#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import pprint
import traceback
import typing
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.validation.ir import elements
from cmk.gui.validation.ir.elements import FormElement
from cmk.gui.validation.ir.valuespec_to_ir import valuespec_to_ir
from cmk.gui.validation.visitors.vue_lib import GenericComponent
from cmk.gui.valuespec import ValueSpec

VueVisitorMethodResult = tuple[GenericComponent, Any]
VueVisitorMethod = typing.Callable[[FormElement, Any], VueVisitorMethodResult]


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    component: dict[str, Any]


@dataclass
class ValidationError:
    message: str
    field_id: str | None = None

    def __hash__(self) -> int:
        return hash(f"{self.message}")

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)


class VueGeneratingVisitor:
    """Creates vue representation. Including value and validation info"""

    _do_validate: bool
    _vue_config: GenericComponent
    _raw_value: Any
    _debug_indent = 0

    def __init__(self, ast: FormElement, value: Any, do_validate: bool = True):
        self._do_validate = do_validate
        self._aggregated_validation_errors = set[ValidationError]()
        self._vue_config, self._raw_value = self._visit(ast, value)

    @contextmanager
    def _change_indent(self, size):
        try:
            self._debug_indent += size
            yield
        finally:
            self._debug_indent -= size

    def _log_indent(self, info):
        logger.warning(" " * self._debug_indent + info)

    @property
    def vue_config(self):
        return self._vue_config

    @property
    def raw_value(self):
        return self._raw_value

    @property
    def validation_errors(self) -> set[ValidationError]:
        return self._aggregated_validation_errors

    @typing.final
    def _visit(self, node: FormElement, value: Any) -> tuple[GenericComponent, Any]:
        type_name = self._type_of_node(node)
        visitor: VueVisitorMethod = getattr(self, f"visit_{type_name}", self.generic_visit)

        with self._change_indent(2):
            self._log_indent(f"-> visiting {node.__class__.__name__} {value}")
            # note: result also includes result(s) from leaves
            component_result, raw_value = visitor(node, value)

            with self._change_indent(4):
                if self._do_validate:
                    self._log_indent(f"  validate {node.__class__.__name__}")
                    try:
                        node.validate(raw_value, component_result)
                    except MKUserError as e:
                        error = ValidationError(
                            message=str(e), field_id=e.varname or str(uuid.uuid4())
                        )
                        component_result.validation_errors = [error.message]
                        # The aggregated errors are used within our old GUI which
                        # requires the MKUser error format (field_id + message)
                        self._aggregated_validation_errors.add(error)

        return component_result, raw_value

    @typing.final
    def _type_of_node(self, node: FormElement) -> str:
        name = node.__class__.__name__
        if not name.endswith("Element"):
            raise RuntimeError(f"Class-name of {node} should end in Element, but is {name}")
        return name[:-7].lower()

    @typing.final
    def generic_visit(self, node: FormElement, value: Any) -> tuple[GenericComponent, Any]:
        raise RuntimeError(f"No visit_{self._type_of_node(node)} method defined.")

    @typing.final
    def visit_number(
        self, node: elements.NumberElement, value: int | float
    ) -> VueVisitorMethodResult:
        return (
            GenericComponent(
                node,
                component_type="number",
                config={
                    "value": value,
                    "unit": node.details.unit,
                    "label": node.label.text,
                },
            ),
            value,
        )

    def visit_tuple(self, node: elements.TupleElement, values: tuple) -> VueVisitorMethodResult:
        raw_value = []
        component_elements = []
        for element, value in zip(node.details.elements, values):
            component_result, component_value = self._visit(element, value)
            component_elements.append(asdict(component_result))
            raw_value.append(component_value)

        return (
            GenericComponent(
                node,
                component_type="list",
                config={
                    "elements": component_elements,
                },
            ),
            tuple(raw_value),
        )

    def visit_typeddictionary(
        self, node: elements.TypedDictionaryElement, values: dict[str, Any]
    ) -> VueVisitorMethodResult:
        dict_elements = []
        raw_value = {}
        for key_spec, field_node in node.details.elements:
            is_active = key_spec.name in values
            if is_active:
                key_value = values[key_spec.name]
            else:
                key_value = field_node.details.default_value

            component_result, component_value = self._visit(field_node, key_value)
            raw_value[key_spec.name] = component_value
            dict_elements.append(
                {
                    "key_spec": key_spec,
                    "is_active": is_active,
                    "component": asdict(component_result),
                }
            )

        return (
            GenericComponent(
                node,
                component_type="dictionary",
                config={"elements": dict_elements},
            ),
            raw_value,
        )

    def visit_legacyvaluespec(
        self, node: elements.LegacyValueSpecElement, value: Any
    ) -> VueVisitorMethodResult:
        """
        The legacy valuespec requires a special handling to compute the actual value
        If the value contains the key 'input_context' it comes from the frontend form.
        This requires the value to be evaluated with the legacy valuespec and the varprefix system.
        """
        config: dict[str, Any] = {}
        if isinstance(value, dict) and "input_context" in value:
            with request.stashed_vars():
                varprefix = value.get("varprefix", "")
                for url_key, url_value in value.get("input_context", {}).items():
                    request.set_var(url_key, url_value)

                try:
                    value = node.details.valuespec.from_html_vars(varprefix)
                    node.details.valuespec.validate_datatype(value, varprefix)
                    node.details.valuespec.validate_value(value, varprefix)
                except MKUserError as e:
                    config["validation_errors"] = [str(e)]
                    with output_funnel.plugged():
                        # Keep in mind that this default value is actually not used,
                        # but replaced by the request vars
                        node.details.valuespec.render_input(
                            varprefix, node.details.valuespec.default_value()
                        )
                        config["html"] = output_funnel.drain()
                        config["varprefix"] = varprefix
                    return (
                        GenericComponent(node, component_type="legacy_valuespec", config=config),
                        value,
                    )

        varprefix = f"legacy_varprefix_{uuid.uuid4()}"
        with output_funnel.plugged():
            node.details.valuespec.render_input(varprefix, value)
            config["html"] = output_funnel.drain()
            config["varprefix"] = varprefix

        return GenericComponent(node, component_type="legacy_valuespec", config=config), value

    def visit_checkbox(self, node: elements.CheckboxElement, value: bool) -> VueVisitorMethodResult:
        return (
            GenericComponent(
                node,
                component_type="checkbox",
                config={"value": value, "label": node.details.label_text},
            ),
            value,
        )


def create_vue_visitor(
    valuespec: ValueSpec, value: Any, do_validate: bool = True
) -> VueGeneratingVisitor:
    logger.warning("CREATE VUE VISITOR %s", pprint.pformat(value))
    ast = valuespec_to_ir(valuespec, stack=[], name="o")
    vue_visitor = VueGeneratingVisitor(ast, value, do_validate=do_validate)
    logger.warning("VISITOR RAW VALUE %s", pprint.pformat(vue_visitor.raw_value))
    return vue_visitor


def process_validation_errors(vue_visitor: VueGeneratingVisitor) -> None:
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


def create_vue_app_config(vue_visitor: VueGeneratingVisitor, app_id: str) -> dict[str, Any]:
    return asdict(
        VueAppConfig(id=app_id, app_name="demo", component=asdict(vue_visitor.vue_config))
    )


def render_vue(valuespec, field_id, value, do_validate=False):
    logger.warning("RENDER APP CONFIG")
    try:
        vue_visitor = create_vue_visitor(valuespec, value, do_validate=do_validate)
        vue_app_config = create_vue_app_config(vue_visitor, field_id)
        logger.warning("%s", pprint.pformat(vue_app_config, width=180))
        html.div("", data_cmk_vue_app=json.dumps(vue_app_config))
    except Exception:
        # Debug only. This block will vanish
        logger.warning("".join(traceback.format_exc()))
