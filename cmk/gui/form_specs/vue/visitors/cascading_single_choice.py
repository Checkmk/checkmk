from typing import Any, Callable, Sequence

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
from cmk.gui.form_specs.vue.utils import get_title_and_help, get_visitor
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1.form_specs import CascadingSingleChoice, DefaultValue, InputHint


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
        selected_value = default_value

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
        title, help_text = get_title_and_help(self.form_spec)
        vue_elements = []
        selected_name, selected_value = value

        for element in self.form_spec.elements:
            element_visitor = get_visitor(element.parameter_form, self.options)
            element_value = element_visitor.parse_value(
                default_value if selected_name != element.name else selected_value
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

            element_visitor = get_visitor(element.parameter_form, self.options)
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

            element_visitor = get_visitor(element.parameter_form, self.options)
            element_value = element_visitor.parse_value(selected_value)
            disk_value = element_visitor.to_disk(element_value)

        return (selected_name, disk_value)
