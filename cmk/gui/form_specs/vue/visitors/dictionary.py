from typing import Any, Callable, Mapping, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DataForDisk,
    DataOrigin,
    DEFAULT_VALUE,
    default_value,
    Value,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import compute_validation_errors, get_title_and_help, get_visitor

from cmk.rulesets.v1.form_specs import Dictionary


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
            value = {key: default_value for key, el in self.form_spec.elements.items() if el.required}

        if not isinstance(value, dict):
            raise TypeError(f"Expected a dictionary, got {type(value)}")

        return value

    def to_vue(self, value: dict[str, object]) -> tuple[VueComponents.FormSpec, Value]:
        title, help_text = get_title_and_help(self.form_spec)
        elements_keyspec = []
        vue_values = {}

        for key_name, dict_element in self.form_spec.elements.items():
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in value
            element_value = element_visitor.parse_value(
                value[key_name] if is_active else default_value
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
        return compute_validation_errors(self._validators(), value)

    def validate(self, value: dict[str, object]) -> list[VueComponents.ValidationMessage]:
        element_validations = [*self._validate_elements(value)]

        for key_name, dict_element in self.form_spec.elements.items():
            if key_name not in value:
                continue

            element_visitor = get_visitor(dict_element.parameter_form, self.options)
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
            element_visitor = get_visitor(dict_element.parameter_form, self.options)
            is_active = key_name in value
            if is_active:
                element_value = element_visitor.parse_value(value[key_name])
                disk_values[key_name] = element_visitor.to_disk(element_value)

        return disk_values
