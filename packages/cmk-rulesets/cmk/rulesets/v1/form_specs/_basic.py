#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from dataclasses import dataclass
from enum import auto, Enum
from typing import ClassVar, Literal, Sequence, TypeVar

from .._localize import Localizable
from ._base import DefaultValue, FormSpec, InputHint, Prefill


@dataclass(frozen=True, kw_only=True)
class BooleanChoice(FormSpec[bool]):
    """Specifies a form for configuring a choice between boolean values

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        prefill: Value to pre-populate the choice with.
        migrate: Transformation of the stored configuration
    """

    label: Localizable | None = None
    prefill: DefaultValue[bool] = DefaultValue(False)


class SIMagnitude(Enum):
    BYTE = auto()
    KILO = auto()
    MEGA = auto()
    GIGA = auto()
    TERA = auto()
    PETA = auto()
    EXA = auto()
    ZETTA = auto()
    YOTTA = auto()


class IECMagnitude(Enum):
    BYTE = auto()
    KIBI = auto()
    MEBI = auto()
    GIBI = auto()
    TEBI = auto()
    PEBI = auto()
    EXBI = auto()
    ZEBI = auto()
    YOBI = auto()


@dataclass(frozen=True, kw_only=True)
class DataSize(FormSpec[int]):
    """Specifies an input field for data storage capacity

    Args:
        label: Text displayed as an extension to the input field
        displayed_magnitudes: Magnitudes of data that can be entered in the UI
        prefill: Value in bytes to pre-populate the form field with.
    """

    label: Localizable | None = None
    displayed_magnitudes: Sequence[SIMagnitude] | Sequence[IECMagnitude]
    prefill: Prefill[int] = InputHint(0)


@dataclass(frozen=True, kw_only=True)
class FileUpload(FormSpec[tuple[str, str, bytes]]):
    """Specifies a file upload form.

    Args:
        extensions: The extensions of the files to choose from. If set to `None`,
            all extensions are selectable.
        mime_types: The allowed mime types of uploaded files. If set to `None`,
            all mime types will be uploadable.

    Consumer model:
        **Type**: ``tuple[str, str, bytes]``

        The configured value will be presented as a 3-tuple consisting of the name of
        the uploaded file, its mime type, and the files content as bytes.

        **Example**: Choosing a pem file to upload would result
        in::

            (
                "my_cert.pem",
                "application/octet-stream",
                b"-----BEGIN CERTIFICATE-----\\n....",
            )

    """

    extensions: tuple[str, ...] | None = None
    mime_types: tuple[str, ...] | None = None


_FixedValueT = TypeVar("_FixedValueT", int, float, str, bool, None)


@dataclass(frozen=True, kw_only=True)
class FixedValue(FormSpec[_FixedValueT]):
    """
    Specifies a fixed non-editable value

    Can be used in a CascadingSingleChoice and Dictionary to represent a fixed value option.

    Args:
        value: Atomic value produced by the form spec
        label: Text displayed underneath the title
    """

    value: _FixedValueT
    label: Localizable | None = None

    def __post_init__(self) -> None:
        try:
            ast.literal_eval(repr(self.value))
        except (
            ValueError,
            TypeError,
            SyntaxError,
            MemoryError,
            RecursionError,
        ) as exc:
            raise ValueError("FixedValue value is not serializable.") from exc


@dataclass(frozen=True, kw_only=True)
class Float(FormSpec[float]):
    """Specifies an input field for floating point numbers

    Args:
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
        prefill: Value to pre-populate the form field with.
    """

    label: Localizable | None = None
    unit: Localizable | None = None

    prefill: Prefill[float] = InputHint(0.0)


@dataclass(frozen=True, kw_only=True)
class HostState(FormSpec[Literal[0, 1, 2]]):
    """Specifies the configuration of a host state.

    >>> state_form_spec = HostState(
    ...     title=Localizable("Host state"),
    ...     prefill=DefaultValue(HostState.UP),
    ... )
    """

    UP: ClassVar = 0
    DOWN: ClassVar = 1
    UNREACH: ClassVar = 2

    prefill: DefaultValue[Literal[0, 1, 2]] = DefaultValue(0)


@dataclass(frozen=True, kw_only=True)
class Integer(FormSpec[int]):
    """Specifies an input field for whole numbers

    Args:
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
        prefill: Value to pre-populate the form field with.

    Consumer model:
        **Type**: ``int``

        The configured value will be presented as an integer to consumers.
    """

    label: Localizable | None = None
    unit: Localizable | None = None
    prefill: Prefill[int] = InputHint(0)


@dataclass(frozen=True, kw_only=True)
class MultilineText(FormSpec[str]):
    """Specifies a multiline text form

    Args:
        monospaced: Display text in the form as monospaced
        macro_support: Hint in the UI that macros can be used in the field.
            Replacing the macros in the plugin is a responsibility of the plugin developer.
        label: Text displayed in front of the input field
        prefill: Value to pre-populate the form field with.

    Consumer model:
        **Type**: ``str``

        The configured value will be presented as a string.

        **Example**: Inputting "some text" in a MultilineText form would result
        in::

            "some text\\n"
    """

    monospaced: bool = False
    macro_support: bool = False

    label: Localizable | None = None

    prefill: Prefill[str] = InputHint("")


@dataclass(frozen=True, kw_only=True)
class Percentage(FormSpec[float]):
    """Specifies an input field for percentages

    Args:
        label: Text displayed in front of the input field
        prefill: Value to pre-populate the form field with.
    """

    label: Localizable | None = None

    prefill: Prefill[float] = InputHint(0.0)


class MatchingScope(Enum):
    PREFIX = auto()
    INFIX = auto()
    FULL = auto()


@dataclass(frozen=True, kw_only=True)
class RegularExpression(FormSpec[str]):
    """
    Specifies an input field for regular expressions

    Args:
        predefined_help_text: Adds pre-formulated help text on how the pattern will be used to match
                              for commonly used matching behavior.
        label: Text displayed as an extension to the input field
        prefill: Value to pre-populate the form field with.
    """

    predefined_help_text: MatchingScope
    label: Localizable | None = None

    prefill: Prefill[str] = InputHint("")


@dataclass(frozen=True, kw_only=True)
class ServiceState(FormSpec[Literal[0, 1, 2, 3]]):
    """Specifies the configuration of a service state.

    >>> state_form_spec = ServiceState(
    ...     title=Localizable("State if somthing happens"),
    ...     prefill=DefaultValue(ServiceState.WARN),
    ... )
    """

    OK: ClassVar = 0
    WARN: ClassVar = 1
    CRIT: ClassVar = 2
    UNKNOWN: ClassVar = 3

    prefill: DefaultValue[Literal[0, 1, 2, 3]] = DefaultValue(0)


@dataclass(frozen=True, kw_only=True)
class String(FormSpec[str]):
    """
    Args:
        label: Text displayed in front of the input field
        macro_support: Hint in the UI that macros can be used in the field.
            Replacing the macros in the plugin is a responsibility of the plugin developer.
        prefill: Value to pre-populate the form field with.
    """

    label: Localizable | None = None
    macro_support: bool = False

    prefill: Prefill[str] = InputHint("")


class TimeMagnitude(Enum):
    MILLISECOND = auto()
    SECOND = auto()
    MINUTE = auto()
    HOUR = auto()
    DAY = auto()


@dataclass(frozen=True, kw_only=True)
class TimeSpan(FormSpec[float]):
    """Specifies an input field for time span

    Args:
        label: Text displayed as an extension to the input field
        displayed_magnitudes: Units that can be configured in the UI. All of the listed units can be
                        configured and the value is the sum of the configured fields in seconds.
        prefill: Value in seconds to pre-populate the form fields with.

    Consumer model:
        **Type**: ``float``

        The configured value will be presented as a float to consumers.
    """

    label: Localizable | None = None
    displayed_magnitudes: Sequence[TimeMagnitude]
    prefill: Prefill[float] = InputHint(0.0)


class InvalidElementMode(Enum):
    KEEP = auto()
    COMPLAIN = auto()


@dataclass
class InvalidElementValidator:
    mode: InvalidElementMode = InvalidElementMode.COMPLAIN
    display: Localizable | None = None
    error_msg: Localizable | None = None


@dataclass(frozen=True)
class SingleChoiceElement:
    """Specifies an element of a single choice form

    Args:
        name: Identifier of the SingleChoiceElement. Must be a valid Python identifier.
        title: Human readable title that will be shown in the UI
    """

    name: str
    title: Localizable

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"'{self.name}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)
class SingleChoice(FormSpec[str]):
    """Specification for a (single-)selection from multiple options

    Args:
        elements: Elements to choose from
        no_elements_text: Text to show if no elements are given
        frozen: If the value can be changed after initial configuration, e.g. for identifiers
        label: Text displayed in front of the input field
        prefill: Pre-selected choice. Must be one of the elements names.
        deprecated_elements: Elements that can still be present in stored user configurations, but
                             are no longer offered
        invalid_element_validation: Validate if the selected value is still offered as a choice
    """

    elements: Sequence[SingleChoiceElement]
    no_elements_text: Localizable | None = None

    frozen: bool = False

    label: Localizable | None = None

    prefill: DefaultValue[str] | InputHint[Localizable] = InputHint(Localizable("Please choose"))

    deprecated_elements: tuple[str, ...] | None = None
    invalid_element_validation: InvalidElementValidator | None = None

    def __post_init__(self) -> None:
        valid = {elem.name for elem in self.elements}
        if isinstance(self.prefill, DefaultValue) and self.prefill.value not in valid:
            raise ValueError(
                f"Invalid default: {self.prefill.value!r}, choose from {', '.join(valid)}"
            )
