#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module includes classes which each represent a specific HTML form element.

Each class is a subclass of the base class 'FormElement', providing structure and behavior
specific to a particular type of form element (such as text inputs, checkboxes, select dropdowns,
radio elements, etc.).

The 'FormElement' class hierarchy builds complex form structures, arranged as a tree to represent
HTML forms.

Don't create instances of 'elements' module classes manually. Instead, use compiler functions
like found in 'valuespec_to_ir'. This maintains the resulting form's accuracy and integrity.
Manual instantiation could cause errors or inconsistencies.
"""
import dataclasses
import typing
from collections.abc import Container

from cmk.gui.valuespec import ValueSpec

T = typing.TypeVar("T")
K = typing.TypeVar("K")
V = typing.TypeVar("V")

MetaData = dict[str, str | None]


@dataclasses.dataclass
class Details(typing.Generic[T]):
    help: str | None
    label_text: str | None
    default_value: typing.Callable[[], T] | None


# TODO: improve typing
Validator = typing.Callable[[typing.Any, typing.Any], None]
ValidationError = str


@dataclasses.dataclass
class FormElement:
    ident: str
    details: Details
    validators: list[Validator] | None

    @classmethod
    def render_options(cls, **kwargs: typing.Any) -> dict[str, type["Details | FormElement"]]:
        hints = typing.get_type_hints(cls)
        details_cls = hints["details"]
        details_attributes = {name: None for name in details_cls.__dataclass_fields__}
        details_attributes.update(kwargs)
        detail_instance = details_cls(**details_attributes)
        return {
            "details": detail_instance,
            "ir_class": cls,
        }

    @property
    def label(self) -> "LabelElement":
        return LabelElement(
            ident=f"label_{self.ident}",
            for_=self.ident,
            text=self.details.label_text if self.details else None,
            validators=None,
            details=self.details,
        )

    def validate(self, value: typing.Any, node_info: typing.Any) -> list:
        if self.validators is None:
            return []
        # Note: since this code will be reworked soon -> don't care about typing
        errors: list = []
        for validator in self.validators:
            if result := validator(value, node_info):
                errors.append(result)
        return errors


@dataclasses.dataclass
class NullElement(FormElement):
    pass


@dataclasses.dataclass
class SelectOption:
    value: str
    label: str


@dataclasses.dataclass
class SelectDetails(Details):
    options: list[SelectOption]


@dataclasses.dataclass
class SelectElement(FormElement):
    details: SelectDetails


@dataclasses.dataclass
class DictionaryKeySpec:
    name: str
    optional: bool = True


@dataclasses.dataclass
class TypedDictionaryDetails(Details):
    elements: list[tuple[DictionaryKeySpec, FormElement]]


@dataclasses.dataclass
class TypedDictionaryElement(FormElement):
    details: TypedDictionaryDetails


@dataclasses.dataclass
class DictionaryDetails(Details):
    key: FormElement | None = None
    value: FormElement | None = None


@dataclasses.dataclass
class DictionaryElement(FormElement):
    details: DictionaryDetails


@dataclasses.dataclass
class CheckboxElement(FormElement):
    pass


@dataclasses.dataclass
class AgeDetails(Details):
    display: Container[typing.Literal["days", "hours", "minutes", "seconds"]] = dataclasses.field(
        default_factory=lambda: ["days", "hours", "minutes", "seconds"],
    )


@dataclasses.dataclass
class AgeElement(FormElement):
    details: AgeDetails


StringPersonalities = typing.Literal["string", "hostname", "password", "email", "url"]


@dataclasses.dataclass
class StringDetails(Details[str]):
    personality: StringPersonalities
    placeholder: str | None
    min_length: int | None
    max_length: int | None
    pattern: str | None


@dataclasses.dataclass
class StringElement(FormElement):
    details: StringDetails


@dataclasses.dataclass
class EmailElement(StringElement):
    pass


@dataclasses.dataclass
class PasswordElement(StringElement):
    pass


@dataclasses.dataclass
class TimeDetails(Details[tuple[int, int] | None]):
    allow_24_00: bool = False


@dataclasses.dataclass
class TimeElement(FormElement):
    details: TimeDetails


@dataclasses.dataclass
class TextAreaElement(StringElement):
    pass


@dataclasses.dataclass
class HiddenElement(FormElement):
    pass


@dataclasses.dataclass
class NumberDetails(Details[float]):
    le: float | None
    ge: float | None
    lt: float | None
    gt: float | None
    multiple_of: float | None
    type: type
    unit: str


@dataclasses.dataclass
class NumberElement(FormElement):
    details: NumberDetails


@dataclasses.dataclass
class UnionDetails(Details):
    elements: list[FormElement]


@dataclasses.dataclass
class UnionElement(FormElement):
    details: UnionDetails


@dataclasses.dataclass
class ConstantDetails(Details):
    value: str


@dataclasses.dataclass
class ConstantElement(FormElement):
    details: ConstantDetails


@dataclasses.dataclass
class TaggedUnionEntry:
    title: str
    ident: str
    element: FormElement


@dataclasses.dataclass
class TaggedUnionDetails(Details):
    elements: list[TaggedUnionEntry]


@dataclasses.dataclass
class TaggedUnionElement(FormElement):
    details: TaggedUnionDetails


@dataclasses.dataclass
class TransparentDetails(Details):
    element: FormElement


@dataclasses.dataclass
class TransparentElement(FormElement):
    details: TransparentDetails


@dataclasses.dataclass
class CollapsableDetails(TransparentDetails):
    collapsed: bool


@dataclasses.dataclass
class CollapsableElement(TransparentElement):
    details: CollapsableDetails


@dataclasses.dataclass
class LabelElement(FormElement):
    for_: str
    text: str | None

    @property
    def label(self) -> "LabelElement":
        raise NotImplementedError("Don't make a label of a label.")


@dataclasses.dataclass
class ListDetails(Details):
    entry: FormElement
    max_length: int | None
    min_length: int | None


@dataclasses.dataclass
class ListElement(FormElement):
    details: ListDetails


@dataclasses.dataclass
class TupleDetails(Details[tuple]):
    elements: list[FormElement]


@dataclasses.dataclass
class TupleElement(FormElement):
    details: TupleDetails


@dataclasses.dataclass
class TransformDetails(Details[T]):
    element: FormElement
    convert_to: typing.Callable[[typing.Any], typing.Any]
    convert_from: typing.Callable[[typing.Any], typing.Any]


@dataclasses.dataclass
class TransformElement(FormElement):
    details: TransformDetails


@dataclasses.dataclass
class UrlDetails(StringDetails):
    allowed_schemes: list[str]
    scheme_required: bool
    default_scheme: str | None


@dataclasses.dataclass
class UrlElement(FormElement):
    details: UrlDetails


@dataclasses.dataclass
class TimerangeDetails(Details):
    pass


@dataclasses.dataclass
class TimerangeElement(FormElement):
    details: TimerangeDetails


@dataclasses.dataclass
class LegacyValueSpecDetails(Details):
    valuespec: ValueSpec


@dataclasses.dataclass
class LegacyValueSpecElement(FormElement):
    details: LegacyValueSpecDetails
