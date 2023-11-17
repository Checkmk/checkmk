#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from cmk.rulesets.v1._localize import Localizable


@dataclass(frozen=True)
class Integer:
    """Specifies an input field for whole numbers

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
        prefill_value: Value to pre-populate the form field with. If None, the backend will decide
                       whether to leave the field empty or to prefill it with a canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None
    unit: Localizable | None = None
    prefill_value: int | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True)
class Percentage:
    """Specifies an input field for percentages

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed in front of the input field
        display_precision: How many decimal places to display
        prefill_value: Value to pre-populate the form field with. If None, the backend will decide
                       whether to leave the field empty or to prefill it with a canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None

    display_precision: int | None = None

    prefill_value: float | None = None

    custom_validate: Callable[[float], object] | None = None


@dataclass(frozen=True)
class TextInput:
    """
    Args:
        title: Human readable title
        label: Text displayed in front of the input field
        help_text: Description to help the user with the configuration
        input_hint: A short hint to aid the user with data entry (e.g. an example)
        prefill_value: Value to pre-populate the form field with. If None, the backend will decide
                       whether to leave the field empty or to prefill it with a canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    label: Localizable | None = None
    help_text: Localizable | None = None
    input_hint: str | None = None

    prefill_value: str | None = None

    custom_validate: Callable[[str], object] | None = None


@dataclass(frozen=True)
class Tuple:
    elements: Sequence["FormSpec"]

    title: Localizable | None = None
    help_text: Localizable | None = None

    custom_validate: Callable[[tuple[object, ...]], object] | None = None


class InvalidElementMode(enum.Enum):
    KEEP = enum.auto()
    COMPLAIN = enum.auto()


@dataclass
class InvalidElementValidator:
    mode: InvalidElementMode = InvalidElementMode.COMPLAIN
    display: Localizable | None = None
    error_msg: Localizable | None = None


_DropdownChoiceElementType = str | int | float | bool | enum.Enum | None


@dataclass(frozen=True)
class DropdownChoiceElement:
    choice: _DropdownChoiceElementType
    display: Localizable


@dataclass(frozen=True)
class DropdownChoice:
    """Specification for a (single-)selection from multiple options

    Args:
        elements: Elements to choose from
        no_elements_text: Text to show if no elements are given
        frozen: If the value can be changed after initial configuration, e.g. for identifiers
        title: Human readable title
        label: Text displayed in front of the input field
        help_text: Description to help the user with the configuration
        prefill_selection: Pre-selected choice.
        deprecated_elements: Elements that can still be present in stored user configurations, but
                             are no longer offered
        invalid_element_validation: Validate if the selected value is still offered as a choice
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    elements: Sequence[DropdownChoiceElement]
    no_elements_text: Localizable | None = None

    frozen: bool = False

    title: Localizable | None = None
    label: Localizable | None = None
    help_text: Localizable | None = None

    prefill_selection: _DropdownChoiceElementType = None

    deprecated_elements: Sequence[_DropdownChoiceElementType] | None = None
    invalid_element_validation: InvalidElementValidator | None = None
    custom_validate: Callable[[_DropdownChoiceElementType], object] | None = None


@dataclass(frozen=True)
class CascadingDropdownElement:
    ident: str
    parameter_form: "FormSpec"


@dataclass(frozen=True)
class CascadingDropdown:
    """Specification for a single-selection from multiple options. Selection is another spec

    Args:
        elements: Elements to choose from
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed in front of the input field
        prefill_selection: Pre-selected choice. If not set, the user is required to make a selection
    """

    elements: Sequence[CascadingDropdownElement]

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None

    prefill_selection: str | None = None

    def __post_init__(self) -> None:
        avail_idents = [elem.ident for elem in self.elements]
        if self.prefill_selection is not None and self.prefill_selection not in avail_idents:
            raise ValueError(Localizable("Default element is not one of the specified elements"))


@dataclass(frozen=True)
class DictElement:
    """
    Args:
        parameter_form: Configuration specification of this entry
        required: Whether the user has to configure the value in question. If set to False, it may
                  be omitted.
        read_only: Element that can't be edited. Can be used to store the discovered parameters.
        show_more: Only show if "show more" is activated
    """

    parameter_form: "FormSpec"
    required: bool | None = False
    read_only: bool | None = False
    show_more: bool | None = False


@dataclass(frozen=True)
class Dictionary:
    """
    Specifies a (multi-)selection of configuration options.

    Args:
        elements: key-value mapping where the key identifies the selected option and the value
                  specifies how the option can be configured. The key has to be a valid python
                  identifier.
        title: Human readable title
        help_text: Description to help the user with the configuration
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
        deprecated_elements: Elements that can no longer be configured, but aren't removed
                            from the old rules that already have them configured. Can be
                            used when deprecating elements, to avoid breaking the old
                            configurations.
                            They are configured with a list of element keys.
        no_elements_text: Text to show if no elements are specified
    """

    elements: Mapping[str, DictElement]
    title: Localizable | None = None
    help_text: Localizable | None = None

    custom_validate: Callable[[Mapping[str, object]], object] | None = None
    deprecated_elements: Sequence[str] = field(default_factory=list)
    no_elements_text: Localizable | None = None

    def __post_init__(self) -> None:
        for key in self.elements.keys():
            assert key.isidentifier(), f"'{key}' is not a valid python identifier"


class State(enum.Enum):
    # Don't use IntEnum to prevent "state.CRIT < state.UNKNOWN" from evaluating to True.
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3


@dataclass(frozen=True)
class MonitoringState:
    elements: Sequence[DropdownChoiceElement] = field(
        default_factory=lambda: [
            DropdownChoiceElement(choice=state, display=Localizable(state.name)) for state in State
        ]
    )

    title: Localizable | None = None
    label: Localizable | None = None
    help_text: Localizable | None = None

    prefill_value: State = State.OK


@dataclass(frozen=True)
class List:
    """
    Specifies a list of configuration elements of the same type.

    Args:
        spec: Configuration specification of the list elements
        title: Human readable title
        help_text: Description to help the user with the configuration
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
        prefill_value: Value to pre-populate the form field with
        order_editable: Can the elements be reordered in the UI
    """

    parameter_form: "FormSpec"
    title: Localizable | None = None
    help_text: Localizable | None = None

    custom_validate: Callable[[Sequence[object]], object] | None = None
    prefill_value: Sequence[object] | None = None
    order_editable: bool = True


ItemFormSpec = TextInput | DropdownChoice


FormSpec = (
    Integer
    | Percentage
    | TextInput
    | Tuple
    | DropdownChoice
    | CascadingDropdown
    | Dictionary
    | MonitoringState
    | List
)
