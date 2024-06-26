from typing import Any, Callable, Sequence

from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DataForDisk,
    DataOrigin,
    DEFAULT_VALUE,
    Value,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import compute_validation_errors, get_title_and_help
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1.form_specs import String


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
        title, help_text = get_title_and_help(self.form_spec)
        return (
            VueComponents.String(
                title=title, help=help_text, validators=build_vue_validators(self._validators())
            ),
            value,
        )

    def validate(self, value: str) -> list[VueComponents.ValidationMessage]:
        return compute_validation_errors(self._validators(), value)

    def to_disk(self, value: str) -> DataForDisk:
        return value
