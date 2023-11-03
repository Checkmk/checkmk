#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cmk.rulesets.v1._localize import Localizable


@dataclass(frozen=True)
class Integer:
    """Specifies an input field for whole numbers

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
        default_value: Default value to use if no number is entered by the user. If None, the
                       backend will decide whether to leave the field empty or to prefill it with a
                       canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None
    unit: Localizable | None = None
    default_value: int | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True)
class Percentage:
    """Specifies an input field for percentages

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed in front of the input field
        display_precision: How many decimal places to display
        default_value: Default value to use if no number is entered by the user. If None, the
                       backend will decide whether to leave the field empty or to prefill it with a
                       canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None

    display_precision: int | None = None

    default_value: float | None = None

    custom_validate: Callable[[float], object] | None = None


@dataclass(frozen=True)
class TextInput:
    """
    Args:
        title: Human readable title
        label: Text displayed in front of the input field
        help_text: Description to help the user with the configuration
        input_hint: A short hint to aid the user with data entry (e.g. an example)
        default_value: Default value to use if no text is entered by the user. If None, the backend
                       will decide whether to leave the field empty or to prefill it with a
                       canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    label: Localizable | None = None
    help_text: Localizable | None = None
    input_hint: str | None = None

    default_value: str | None = None

    custom_validate: Callable[[str], object] | None = None


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
        deprecated_elements: Elements that can still be present in stored user configurations, but
                             are no longer offered
        frozen: If the value can be changed after initial configuration, e.g. for identifiers
        title: Human readable title
        label: Text displayed in front of the input field
        help_text: Description to help the user with the configuration
        default_element: Default selection
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

    default_element: _DropdownChoiceElementType = None

    deprecated_elements: Sequence[Any] | None = None
    invalid_element_validation: InvalidElementValidator | None = None
    custom_validate: Callable[[_DropdownChoiceElementType], object] | None = None


@dataclass(frozen=True)
class DictElement:
    """
    Args:
        spec: Configuration specification of this entry
        required: Whether the user has to configure the value in question. If set to False, it may
                  be omitted.
        show_more: Only show if "show more" is activated
    """

    spec: "ValueSpec"
    required: bool | None = False
    ignored: bool | None = False  # TODO check if hidden_keys are needed in addition
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
        no_elements_text: Text to show if no elements are specified
    """

    elements: Mapping[str, DictElement]
    title: Localizable | None = None
    help_text: Localizable | None = None

    custom_validate: Callable[[Mapping[str, object]], object] | None = None
    no_elements_text: Localizable | None = None

    def __post_init__(self):
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

    default_value: State = State.OK


ItemSpec = TextInput | DropdownChoice

ValueSpec = Integer | Percentage | TextInput | DropdownChoice | Dictionary | MonitoringState
