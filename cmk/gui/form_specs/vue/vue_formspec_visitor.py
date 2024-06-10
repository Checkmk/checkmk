#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
import pprint
import traceback
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import auto, Enum
from typing import Any, Generic, Mapping, Sequence, TypeVar

from cmk.utils.exceptions import MKGeneralException

import cmk.gui.form_specs.vue.type_defs.vue_formspec_components as VueComponents
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.private.definitions import LegacyValueSpec
from cmk.gui.form_specs.private.validators import IsFloat, IsInteger
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


class DataOrigin(Enum):
    DISK = auto()
    FRONTEND = auto()


@dataclass
class VisitorOptions:
    # Depending on the origin, we will call the migrate function
    data_origin: DataOrigin


@dataclass(kw_only=True)
class VueAppConfig:
    id: str
    app_name: str
    form_spec: VueComponents.FormSpec
    model_value: Any
    validation_messages: Any


class FormSpecVisitor(abc.ABC, Generic[ModelT]):
    @abc.abstractmethod
    def __init__(self, form_spec: FormSpec[ModelT], options: VisitorOptions) -> None: ...

    @abc.abstractmethod
    def parse_value(self, value: Any) -> ModelT: ...

    @abc.abstractmethod
    def to_vue(self, value: ModelT) -> tuple[VueComponents.FormSpec, Value]: ...

    @abc.abstractmethod
    def validate(self, value: ModelT) -> list[VueComponents.ValidationMessage]: ...

    @abc.abstractmethod
    def to_disk(self, value: ModelT) -> DataForDisk: ...


def _get_visitor(form_spec: FormSpec, options: VisitorOptions) -> FormSpecVisitor:
    supported_form_spec = _convert_to_supported_form_spec(form_spec)
    visitor = _form_specs_visitor_registry.get(supported_form_spec.__class__)
    if visitor is None:
        raise MKGeneralException(f"No visitor for {supported_form_spec.__class__.__name__}")
    return visitor(supported_form_spec, options)


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
    validators: Sequence[Callable[[ModelT], object]],
    raw_value: Any,
) -> list[VueComponents.ValidationMessage]:
    return [
        VueComponents.ValidationMessage(location=[""], message=x)
        for x in _optional_validation(validators, raw_value)
        if x is not None
    ]


class IntegerVisitor(FormSpecVisitor):
    def __init__(self, form_spec: Integer, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def parse_value(self, value: Any) -> int:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = self.form_spec.prefill.value

        if not isinstance(value, int):
            raise TypeError(f"Expected a integer, got {type(value)}")

        return value

    def _validators(self) -> Sequence[Callable[[int], object]]:
        return [IsInteger()] + (
            list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []
        )

    def to_vue(self, value: int) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        return (
            VueComponents.Integer(
                title=title, help=help_text, validators=build_vue_validators(self._validators())
            ),
            value,
        )

    def validate(self, value: int) -> list[VueComponents.ValidationMessage]:
        return _compute_validation_errors(self._validators(), value)

    def to_disk(self, value: int) -> DataForDisk:
        return value


class FloatVisitor(FormSpecVisitor):
    def __init__(self, form_spec: Float, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[float], object]]:
        return [IsFloat()] + (
            list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []
        )

    def parse_value(self, value: Any) -> float:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = self.form_spec.prefill.value

        if not isinstance(value, float):
            raise TypeError(f"Expected a float, got {type(value)}")

        return value

    def to_vue(self, value: float) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        return (
            VueComponents.Float(
                title=title, help=help_text, validators=build_vue_validators(self._validators())
            ),
            value,
        )

    def validate(self, value: float) -> list[VueComponents.ValidationMessage]:
        return _compute_validation_errors(self._validators(), value)

    def to_disk(self, value: float) -> DataForDisk:
        return value


class StringVisitor(FormSpecVisitor):
    def __init__(self, form_spec: String, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def parse_value(self, value: Any) -> str:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = self.form_spec.prefill.value

        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value)}")

        return str(value)

    def _validators(self) -> Sequence[Callable[[str], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def to_vue(self, value: str) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        return (
            VueComponents.String(
                title=title, help=help_text, validators=build_vue_validators(self._validators())
            ),
            value,
        )

    def validate(self, value: str) -> list[VueComponents.ValidationMessage]:
        return _compute_validation_errors(self._validators(), value)

    def to_disk(self, value: str) -> DataForDisk:
        return value


class DictionaryVisitor(FormSpecVisitor):
    def __init__(self, form_spec: Dictionary, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[Mapping[str, object]], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> dict[str, object]:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = {}

        if not isinstance(value, dict):
            raise TypeError(f"Expected a dictionary, got {type(value)}")

        return value

    def to_vue(self, value: dict[str, object]) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        elements_keyspec = []
        vue_values = {}

        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = _get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in value
            element_value = element_visitor.parse_value(
                value[key_name] if is_active else _default_value
            )

            element_schema, element_vue_value = element_visitor.to_vue(element_value)

            if is_active:
                vue_values[key_name] = element_vue_value

            elements_keyspec.append(
                VueComponents.DictionaryElement(
                    ident=key_name,
                    default_value=element_vue_value,
                    required=dict_element.required,
                    parameter_form=element_schema,
                )
            )

        return (
            VueComponents.Dictionary(title=title, help=help_text, elements=elements_keyspec),
            vue_values,
        )

    def _validate_elements(self, value: dict[str, object]) -> list[VueComponents.ValidationMessage]:
        return _compute_validation_errors(self._validators(), value)

    def validate(self, value: dict[str, object]) -> list[VueComponents.ValidationMessage]:
        element_validations = [*self._validate_elements(value)]

        for key_name, dict_element in self.form_spec.elements.items():
            if key_name not in value:
                continue

            element_visitor = _get_visitor(dict_element.parameter_form, self.options)
            element_value = element_visitor.parse_value(value[key_name])
            for validation in element_visitor.validate(element_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[key_name] + validation.location,
                        message=validation.message,
                    )
                )

        return element_validations

    def to_disk(self, value: dict[str, object]) -> DataForDisk:
        disk_values = {}

        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = _get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in value
            if is_active:
                element_value = element_visitor.parse_value(value[key_name])
                disk_values[key_name] = element_visitor.to_disk(element_value)

        return disk_values


class SingleChoiceVisitor(FormSpecVisitor):
    def __init__(self, form_spec: SingleChoice, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[str], object]]:
        # TODO: add special __post_init__ / ignored_elements / invalid element
        #      validators for this form spec
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> str:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            if isinstance(self.form_spec.prefill, InputHint):
                value = ""
            else:
                value = self.form_spec.prefill.value

        if not isinstance(value, str):
            raise TypeError(f"Expected a string, got {type(value)}")

        return value

    def to_vue(self, value: str) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        elements = [
            VueComponents.SingleChoiceElement(
                name=element.name,
                title=element.title.localize(translate_to_current_language),
            )
            for element in self.form_spec.elements
        ]
        return (
            VueComponents.SingleChoice(
                title=title,
                help=help_text,
                elements=elements,
                validators=build_vue_validators(self._validators()),
                frozen=self.form_spec.frozen,
            ),
            value,
        )

    def validate(self, value: str) -> list[VueComponents.ValidationMessage]:
        return _compute_validation_errors(self._validators(), value)

    def to_disk(self, value: str) -> DataForDisk:
        return value


class CascadingSingleChoiceVisitor(FormSpecVisitor):
    def __init__(self, form_spec: CascadingSingleChoice, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[tuple[str, object]], object]]:
        # TODO: add special __post_init__ / element validators for this form spec
        return self.form_spec.custom_validate if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> tuple[str, object]:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        selected_name = ""
        selected_value = _default_value

        elements_to_show = []
        if isinstance(value, DEFAULT_VALUE):
            if isinstance(self.form_spec.prefill, InputHint):
                elements_to_show.append(
                    VueComponents.SingleChoiceElement(
                        name="",
                        title=self.form_spec.prefill.value.localize(translate_to_current_language),
                    )
                )
            else:
                assert isinstance(self.form_spec.prefill, DefaultValue)
                selected_name = self.form_spec.prefill.value
        else:
            selected_name, selected_value = value

        return selected_name, selected_value

    def to_vue(self, value: tuple[str, object]) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        vue_elements = []
        selected_name, selected_value = value

        for element in self.form_spec.elements:
            element_visitor = _get_visitor(element.parameter_form, self.options)
            element_value = element_visitor.parse_value(
                _default_value if selected_name != element.name else selected_value
            )
            element_schema, element_vue_value = element_visitor.to_vue(element_value)

            if selected_name == element.name:
                selected_value = element_vue_value

            vue_elements.append(
                VueComponents.CascadingSingleChoiceElement(
                    name=element.name,
                    title=element.title.localize(translate_to_current_language),
                    default_value=element_vue_value,
                    parameter_form=element_schema,
                )
            )

        return (
            VueComponents.CascadingSingleChoice(
                title=title,
                help=help_text,
                elements=vue_elements,
                validators=build_vue_validators(self._validators()),
            ),
            (selected_name, selected_value),
        )

    def validate(self, value: tuple[str, object]) -> list[VueComponents.ValidationMessage]:
        element_validations = []
        selected_name, selected_value = value
        for element in self.form_spec.elements:
            if selected_name != element.name:
                continue

            element_visitor = _get_visitor(element.parameter_form, self.options)
            element_value = element_visitor.parse_value(selected_value)

            for validation in element_visitor.validate(element_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[element.name] + validation.location,
                        message=validation.message,
                    )
                )

        return element_validations

    def to_disk(self, value: tuple[str, object]) -> DataForDisk:
        disk_value: Any = None
        selected_name, selected_value = value
        for element in self.form_spec.elements:
            if selected_name != element.name:
                continue

            element_visitor = _get_visitor(element.parameter_form, self.options)
            element_value = element_visitor.parse_value(selected_value)
            disk_value = element_visitor.to_disk(element_value)

        return (selected_name, disk_value)


class ListVisitor(FormSpecVisitor):
    def __init__(self, form_spec: List, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def _validators(self) -> Sequence[Callable[[list], object]]:
        return list(self.form_spec.custom_validate) if self.form_spec.custom_validate else []

    def parse_value(self, value: Any) -> list:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = []

        if not isinstance(value, list):
            raise TypeError(f"Expected a list, got {type(value)}")

        return value

    def to_vue(self, value: list) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)

        element_visitor = _get_visitor(self.form_spec.element_template, self.options)
        element_default_value = element_visitor.parse_value(_default_value)
        element_schema, element_vue_default_value = element_visitor.to_vue(element_default_value)

        vue_values = []
        for element_value in value:
            parsed_element_value = element_visitor.parse_value(element_value)
            _, element_vue_value = element_visitor.to_vue(parsed_element_value)
            vue_values.append(element_vue_value)

        return (
            VueComponents.List(
                title=title,
                help=help_text,
                element_template=element_schema,
                element_default_value=element_vue_default_value,
                add_element_label=self.form_spec.add_element_label.localize(
                    translate_to_current_language
                ),
                remove_element_label=self.form_spec.remove_element_label.localize(
                    translate_to_current_language
                ),
                no_element_label=self.form_spec.no_element_label.localize(
                    translate_to_current_language
                ),
                editable_order=self.form_spec.editable_order,
            ),
            vue_values,
        )

    def _validate_elements(self, value: list) -> list[VueComponents.ValidationMessage]:
        return _compute_validation_errors(self._validators(), value)

    def validate(self, value: list) -> list[VueComponents.ValidationMessage]:
        element_validations = [*self._validate_elements(value)]
        element_visitor = _get_visitor(self.form_spec.element_template, self.options)

        for idx, element_value in enumerate(value):
            parsed_element_value = element_visitor.parse_value(element_value)
            element_value = element_visitor.parse_value(parsed_element_value)
            for validation in element_visitor.validate(element_value):
                element_validations.append(
                    VueComponents.ValidationMessage(
                        location=[str(idx)] + validation.location, message=validation.message
                    )
                )

        return element_validations

    def to_disk(self, value: list) -> Any:
        disk_values = []
        element_visitor = _get_visitor(self.form_spec.element_template, self.options)

        for element_value in value:
            parsed_element_value = element_visitor.parse_value(element_value)
            element_value = element_visitor.parse_value(parsed_element_value)
            disk_values.append(element_visitor.to_disk(element_value))

        return disk_values


class LegacyValuespecVisitor(FormSpecVisitor):
    def __init__(self, form_spec: LegacyValueSpec, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    def parse_value(self, value: Any) -> Any:
        if self.options.data_origin == DataOrigin.DISK and self.form_spec.migrate:
            value = self.form_spec.migrate(value)

        if isinstance(value, DEFAULT_VALUE):
            value = self.form_spec.valuespec.default_value()

        return value

    def to_vue(self, value: Any) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = _get_title_and_help(self.form_spec)
        config: dict[str, Any] = {}
        if isinstance(value, dict) and "input_context" in value:
            with request.stashed_vars():
                varprefix = value.get("varprefix", "")
                for url_key, url_value in value.get("input_context", {}).items():
                    request.set_var(url_key, url_value)

                try:
                    value = self.form_spec.valuespec.from_html_vars(varprefix)
                except MKUserError as e:
                    user_errors.add(e)
                    with output_funnel.plugged():
                        # Keep in mind that this default value is actually not used,
                        # but replaced by the request vars
                        self.form_spec.valuespec.render_input(
                            varprefix, self.form_spec.valuespec.default_value()
                        )
                        return (
                            VueComponents.LegacyValuespec(
                                title=title,
                                help=help_text,
                                html=output_funnel.drain(),
                                varprefix=varprefix,
                            ),
                            None,
                        )

        varprefix = f"legacy_varprefix_{uuid.uuid4()}"
        with output_funnel.plugged():
            self.form_spec.valuespec.render_input(varprefix, value)
            return (
                VueComponents.LegacyValuespec(
                    title=title,
                    help=help_text,
                    html=output_funnel.drain(),
                    varprefix=varprefix,
                ),
                config,
            )

    def validate(self, value: Any) -> list[VueComponents.ValidationMessage]:
        if isinstance(value, dict) and "input_context" in value:
            with request.stashed_vars():
                varprefix = value.get("varprefix", "")
                for url_key, url_value in value.get("input_context", {}).items():
                    request.set_var(url_key, url_value)

                try:
                    value = self.form_spec.valuespec.from_html_vars(varprefix)
                    self.form_spec.valuespec.validate_datatype(value, varprefix)
                    self.form_spec.valuespec.validate_value(value, varprefix)
                except MKUserError as e:
                    user_errors.add(e)
                    return [VueComponents.ValidationMessage(location=[""], message=str(e))]

        varprefix = f"legacy_varprefix_{uuid.uuid4()}"
        with output_funnel.plugged():
            validation_errors = []
            try:
                self.form_spec.valuespec.render_input(varprefix, value)
            except MKUserError as e:
                validation_errors = [VueComponents.ValidationMessage(location=[""], message=str(e))]
            return validation_errors

    def to_disk(self, value: Any) -> Any:
        return value


_form_specs_visitor_registry: dict[type, type[FormSpecVisitor]] = {}


def register_class(validator_class: type[FormSpec], visitor_class: type[FormSpecVisitor]) -> None:
    _form_specs_visitor_registry[validator_class] = visitor_class


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


def register_form_specs():
    # TODO: add test which checks if all available FormSpecs have a visitor
    register_class(Integer, IntegerVisitor)
    register_class(Dictionary, DictionaryVisitor)
    register_class(String, StringVisitor)
    register_class(Float, FloatVisitor)
    register_class(SingleChoice, SingleChoiceVisitor)
    register_class(CascadingSingleChoice, CascadingSingleChoiceVisitor)
    register_class(List, ListVisitor)
    register_class(LegacyValueSpec, LegacyValuespecVisitor)


register_form_specs()


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


def _process_validation_errors(validation_errors: list[VueComponents.ValidationMessage]) -> None:
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
        if form_spec.migrate:
            value = form_spec.migrate(value)
        visitor = _get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.DISK))
        parsed_value = visitor.parse_value(value)
        vue_component, vue_value = visitor.to_vue(parsed_value)
        validation = visitor.validate(parsed_value) if do_validate else []
        vue_app_config = asdict(
            VueAppConfig(
                id=field_id,
                app_name="form_spec",
                form_spec=vue_component,
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
    visitor = _get_visitor(form_spec, VisitorOptions(data_origin=DataOrigin.FRONTEND))
    _process_validation_errors(visitor.validate(value_from_frontend))
    return visitor.to_disk(value_from_frontend)
