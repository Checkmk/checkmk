#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from cmk.rulesets.v1._localize import Localizable


@dataclass
class DropdownChoice:
    ...


@dataclass(frozen=True)
class TextInput:
    """
    Args:
        title: Human readable title
        label: Text displayed in front of the input field
        help_text: Description to help the user with the configuration
        input_hint: A short hint to aid the user with data entry (e.g. an example)
        default_value: Default text
        custom_validate: Custom validation function. Will be executed in addition to any
                 builtin validation logic. Needs to raise a ValidationError in case
                 validation fails, the return value of the function will not be consumed
    """

    title: Localizable | None = None
    label: Localizable | None = None
    help_text: Localizable | None = None
    input_hint: str | None = None

    default_value: str | None = None

    custom_validate: Callable[[str], object] | None = None


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
                         validation fails, the return value of the function will not be consumed
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
    title: Localizable
    default_value: State = State.OK
    elements: Sequence[tuple[State, str]] = field(
        default_factory=lambda: [(state, state.name) for state in State]
    )


ItemSpec = TextInput | DropdownChoice

ValueSpec = TextInput | DropdownChoice | Dictionary | MonitoringState
