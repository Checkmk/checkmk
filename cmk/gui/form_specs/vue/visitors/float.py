from typing import Any, Callable, Sequence

from cmk.gui.form_specs.private.validators import IsFloat
from cmk.gui.form_specs.vue.autogen_type_defs import vue_formspec_components as VueComponents
from cmk.gui.form_specs.vue.registries import FormSpecVisitor
from cmk.gui.form_specs.vue.type_defs import (
    DataForDisk,
    DataOrigin,
    DEFAULT_VALUE,
    Value,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.utils import compute_validation_errors, get_title_and_help, localize
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1.form_specs import Float


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
        title, help_text = get_title_and_help(self.form_spec)
        return (
            VueComponents.Float(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(self._validators()),
            ),
            value,
        )

    def validate(self, value: float) -> list[VueComponents.ValidationMessage]:
        return compute_validation_errors(self._validators(), value)

    def to_disk(self, value: float) -> DataForDisk:
        return value
