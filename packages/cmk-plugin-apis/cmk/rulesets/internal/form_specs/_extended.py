#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, override, Protocol, runtime_checkable

from cmk.rulesets.v1 import Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictGroup,
    Dictionary,
    FieldSize,
    FormSpec,
    InputHint,
    InvalidElementValidator,
    List,
    MultipleChoiceElement,
    Prefill,
)

# Note: We use Protocols here instead of importing from cmk.shared_typing
# to avoid module layer violations. These Protocols are compatible with
# the dataclasses defined in cmk.shared_typing.vue_formspec_components.
# When using StringAutocompleter, pass an Autocompleter instance from
# cmk.shared_typing.vue_formspec_components.


class AutocompleterParams(Protocol):
    @property
    def show_independent_of_context(self) -> bool | None: ...
    @property
    def strict(self) -> bool | None: ...
    @property
    def escape_regex(self) -> bool | None: ...
    @property
    def world(self) -> str | None: ...
    @property
    def context(self) -> Mapping[str, Any] | None: ...
    @property
    def input_hint(self) -> str | None: ...


class AutocompleterData(Protocol):
    @property
    def ident(self) -> str: ...
    @property
    def params(self) -> AutocompleterParams: ...


class FetchMethod(Protocol):
    @property
    def value(self) -> str: ...


@runtime_checkable
class Autocompleter(Protocol):
    @property
    def data(self) -> AutocompleterData: ...
    @property
    def fetch_method(self) -> FetchMethod | None: ...


class DictionaryGroupLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"
    two_columns = "two_columns"


class ListOfStringsLayout(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"


@dataclass(frozen=True, kw_only=True)
class ListExtended[ModelT](List[ModelT]):
    prefill: DefaultValue[Sequence[ModelT]]


@dataclass(frozen=True, kw_only=True)
class SingleChoiceElementExtended[T]:
    name: T
    title: Title


@dataclass(frozen=True, kw_only=True)
class SingleChoiceExtended[T](FormSpec[T]):
    # SingleChoice:
    elements: (
        Sequence[SingleChoiceElementExtended[T]]
        | Callable[[], Sequence[SingleChoiceElementExtended[T]]]
    )
    no_elements_text: Message | None = None
    frozen: bool = False
    label: Label | None = None
    prefill: DefaultValue[T] | InputHint[Title] = InputHint(Title("Please choose"))
    ignored_elements: tuple[str, ...] = ()
    invalid_element_validation: InvalidElementValidator | None = None


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceExtendedLayout(str, Enum):
    auto = "auto"
    dual_list = "dual_list"
    checkbox_list = "checkbox_list"


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceElementExtended(MultipleChoiceElement):
    """Specifies an element of a multiple choice form.

    It can and should only be used internally when using it to generate MultipleChoiceExtended
    FormSpecs when the input data is not predefined, for example when creating FormSpecs based on
    user input, like for contact groups.
    """

    @override
    def __post_init__(self) -> None:
        pass


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceExtended(FormSpec[Sequence[str]]):
    elements: Sequence[MultipleChoiceElement] | Autocompleter
    show_toggle_all: bool = False
    prefill: DefaultValue[Sequence[str]] = DefaultValue(())
    layout: MultipleChoiceExtendedLayout = MultipleChoiceExtendedLayout.auto

    def __post_init__(self) -> None:
        if not isinstance(self.elements, Autocompleter):
            available_names = {elem.name for elem in self.elements}
            if invalid := set(self.prefill.value) - available_names:
                raise ValueError(f"Invalid prefill element(s): {', '.join(invalid)}")


@dataclass(frozen=True, kw_only=True)
class DictionaryExtended(Dictionary):
    # Usage of default_checked is advised against: if you want an optional
    # element prefilled with options, reconsider and flip your approach. If
    # something should be the default, it should not need configuration. Add
    # complexity (stray from the default) by checking boxes, not unchecking
    # them. Another approach would be to use a cascading single choice with your
    # default preselected.
    default_checked: list[str] | None = None

    @override
    def __post_init__(self) -> None:
        for checked in self.default_checked or []:
            if checked not in self.elements:
                raise ValueError(f"Default checked element '{checked}' is not in elements")


@dataclass(frozen=True, kw_only=True)
class DictGroupExtended(DictGroup):
    """Specification for a group of dictionary elements that are more closely related thematically
    than the other elements. A group is identified by its title and help text.
    """

    layout: DictionaryGroupLayout = DictionaryGroupLayout.horizontal


@dataclass(frozen=True, kw_only=True)
class ListOfStrings(FormSpec[Sequence[str]]):
    string_spec: FormSpec[str]
    layout: ListOfStringsLayout = ListOfStringsLayout.horizontal
    prefill: DefaultValue[Sequence[str]] = DefaultValue([])


@dataclass(frozen=True, kw_only=True)
class SimplePassword(FormSpec[str]):
    """A simple password field FormSpec.

    This is a basic password input that doesn't integrate with the password store.
    For password store integration, use the appropriate GUI-specific form spec.
    """

    pass


@dataclass(frozen=True, kw_only=True)
class StringAutocompleter(FormSpec[str]):
    """A string input with autocomplete support."""

    label: Label | None = None
    macro_support: bool = False
    prefill: Prefill[str] = InputHint("")
    field_size: FieldSize = FieldSize.MEDIUM
    autocompleter: Autocompleter | None = None
