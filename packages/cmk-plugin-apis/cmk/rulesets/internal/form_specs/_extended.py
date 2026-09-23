#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, override

from cmk.rulesets.v1 import Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoiceElement,
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


class FetchMethod(StrEnum):
    ajax_vs_autocomplete = "ajax_vs_autocomplete"
    rest_autocomplete = "rest_autocomplete"


@dataclass(frozen=True, kw_only=True)
class AutocompleterParams:
    show_independent_of_context: bool | None = None
    strict: bool | None = None
    escape_regex: bool | None = None
    literal_search: bool | None = None
    world: str | None = None
    object_type: str | None = None
    context: Mapping[str, object] | None = None
    input_hint: str | None = None


@dataclass(frozen=True, kw_only=True)
class AutocompleterData:
    ident: str
    params: AutocompleterParams


@dataclass(frozen=True, kw_only=True)
class Autocompleter:
    data: AutocompleterData
    fetch_method: FetchMethod = FetchMethod.ajax_vs_autocomplete


class DictionaryGroupLayout(StrEnum):
    horizontal = "horizontal"
    vertical = "vertical"


class ListOfStringsLayout(StrEnum):
    horizontal = "horizontal"
    vertical = "vertical"


class CascadingSingleChoiceLayout(StrEnum):
    vertical = "vertical"
    horizontal = "horizontal"
    button_group = "button_group"


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
class CascadingSingleChoiceElementExtended[ModelT](CascadingSingleChoiceElement[ModelT]):
    """Specifies an element of a single choice cascading form.

    It can and should only be used internally when using it to generate CascadingSingleChoiceExtended
    FormSpecs when the input data is not predefined, for example when creating FormSpecs based on
    user input, like for contact groups.
    """

    @override
    def __post_init__(self) -> None:
        pass


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceExtended(FormSpec[tuple[str, object]]):  # type: ignore[explicit-any]
    elements: (  # type: ignore[explicit-any]
        Sequence[CascadingSingleChoiceElement[Any]]
        | Callable[[], Sequence[CascadingSingleChoiceElement[Any]]]
    )
    no_elements_text: Message = Message("(No choices available)")
    label: Label | None = None
    prefill: DefaultValue[str] | InputHint[Title] = InputHint(Title("Please choose"))
    layout: CascadingSingleChoiceLayout = CascadingSingleChoiceLayout.vertical

    def __post_init__(self) -> None:
        if callable(self.elements):
            return
        available_names = {elem.name for elem in self.elements}
        if isinstance(self.prefill, DefaultValue) and self.prefill.value not in available_names:
            raise ValueError(
                f"Default element {self.prefill.value!r} is not "
                f"one of the specified elements {available_names!r}"
            )


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceExtendedLayout(StrEnum):
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
class DictionaryExtended(Dictionary):  # type: ignore[explicit-any]
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


@dataclass(frozen=True, kw_only=True)
class StringAutocompleter(FormSpec[str]):
    """A string input with autocomplete support."""

    label: Label | None = None
    macro_support: bool = False
    prefill: Prefill[str] = InputHint("")
    field_size: FieldSize = FieldSize.MEDIUM
    autocompleter: Autocompleter | None = None
