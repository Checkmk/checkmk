import abc
from typing import Any, final, Generic, TypeVar

from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.form_specs.vue.type_defs import EmptyValue
from cmk.gui.form_specs.vue.visitors._type_defs import DataForDisk, Value, VisitorOptions

from cmk.ccc.exceptions import MKGeneralException
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs._base import ModelT

FormSpecModel = TypeVar("FormSpecModel", bound=FormSpec[Any])


class FormSpecVisitor(abc.ABC, Generic[FormSpecModel, ModelT]):
    @final
    def __init__(self, form_spec: FormSpecModel, options: VisitorOptions) -> None:
        self.form_spec = form_spec
        self.options = options

    @abc.abstractmethod
    def _parse_value(self, raw_value: object) -> ModelT | EmptyValue: ...

    @final
    def to_vue(self, raw_value: object) -> tuple[VueComponents.FormSpec, Value]:
        return self._to_vue(raw_value, self._parse_value(raw_value))

    @final
    def validate(self, raw_value: object) -> list[VueComponents.ValidationMessage]:
        return self._validate(raw_value, self._parse_value(raw_value))

    @final
    def to_disk(self, raw_value: object) -> DataForDisk:
        parsed_value = self._parse_value(raw_value)
        if isinstance(parsed_value, EmptyValue):
            raise MKGeneralException("Unable to serialize empty value")
        return self._to_disk(raw_value, parsed_value)

    @abc.abstractmethod
    def _to_vue(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> tuple[VueComponents.FormSpec, Value]: ...

    @abc.abstractmethod
    def _validate(
        self, raw_value: object, parsed_value: ModelT | EmptyValue
    ) -> list[VueComponents.ValidationMessage]: ...

    @abc.abstractmethod
    def _to_disk(self, raw_value: object, parsed_value: ModelT) -> DataForDisk: ...
