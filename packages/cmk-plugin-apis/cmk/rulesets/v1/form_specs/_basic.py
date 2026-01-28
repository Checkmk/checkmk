#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from enum import auto, Enum
from keyword import iskeyword
from typing import ClassVar, Literal, TypeVar

from .._localize import Label, Message, Title
from ._base import DefaultValue, FormSpec, InputHint, Prefill

__all__ = [
    "BooleanChoice",
    "SIMagnitude",
    "IECMagnitude",
    "DataSize",
    "FileUpload",
    "FixedValue",
    "Float",
    "HostState",
    "Integer",
    "MultilineText",
    "Percentage",
    "MatchingScope",
    "RegularExpression",
    "ServiceState",
    "FieldSize",
    "String",
    "TimeMagnitude",
    "TimeSpan",
    "InvalidElementMode",
    "InvalidElementValidator",
    "SingleChoiceElement",
    "SingleChoice",
]


@dataclass(frozen=True, kw_only=True)
class BooleanChoice(FormSpec[bool]):
    """Specifies a form for configuring a choice between boolean values.

    Consumer model:
    ***************
        **Type**: ``bool``

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed as an extension to the input field."""
    prefill: DefaultValue[bool] = DefaultValue(False)
    """Value to pre-populate the form field with."""


class SIMagnitude(Enum):
    """SI magnitudes for data storage capacity.
    These scale the value using powers of 1000."""

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
    """IEC magnitudes for memory capacity.
    These scale the value using powers of 1024."""

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

    Consumer model:
    ***************
      **Type**: ``int``

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed as an extension to the input field"""
    displayed_magnitudes: Sequence[SIMagnitude] | Sequence[IECMagnitude]
    """Magnitudes of data that can be entered in the UI"""
    prefill: Prefill[int] = InputHint(0)
    """Value in bytes to pre-populate the form field with."""


@dataclass(frozen=True, kw_only=True)
class FileUpload(FormSpec[tuple[str, str, bytes]]):
    """Specifies a file upload form.

    Consumer model:
    ***************

    The configured value will be presented as a 3-tuple consisting of the name of
    the uploaded file, its mime type, and the files content as bytes.

    **Type**: ``tuple[str, str, bytes]``

    **Example**: Choosing a pem file to upload would result
    in::

       (
            "my_cert.pem",
            "application/octet-stream",
            b"-----BEGIN CERTIFICATE-----\\n....",
        )

    Arguments:
    **********
    """

    extensions: tuple[str, ...] | None = None
    """The extensions of the files to choose from. If set to `None`,
    all extensions are selectable."""
    mime_types: tuple[str, ...] | None = None
    """The allowed mime types of uploaded files. If set to `None`,
    all mime types will be uploadable."""


_FixedValueT = TypeVar("_FixedValueT", int, float, str, bool, None)


@dataclass(frozen=True, kw_only=True)
class FixedValue(FormSpec[_FixedValueT]):
    """
    Specifies a fixed non-editable value.

    Can be used in a CascadingSingleChoice and Dictionary to represent a fixed value option.

    Consumer model:
    ***************
    The consumer model is equal to the configuration model, i.e. the value that it contains.

    Arguments:
    **********
    """

    value: _FixedValueT
    """Atomic value produced by the form spec"""
    label: Label | None = None
    """Text displayed underneath the title."""

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
    """Specifies an input field for floating point numbers.

    Consumer model:
    ***************
    **Type**: ``float``

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed as an extension to the input field."""
    unit_symbol: str = ""
    """Unit symbol to add to the input field."""

    prefill: Prefill[float] = InputHint(0.0)
    """Value to pre-populate the form field with."""


@dataclass(frozen=True, kw_only=True)
class HostState(FormSpec[Literal[0, 1, 2]]):
    """Specifies the configuration of a host state.

    Consumer model:
    ***************
    **Type**: ``Literal[0, 1, 2]``

    Example:
    ********

    >>> state_form_spec = HostState(
    ...     title=Title("Host state"),
    ...     prefill=DefaultValue(HostState.UP),
    ... )

    Arguments:
    **********
    """

    UP: ClassVar[Literal[0]] = 0
    DOWN: ClassVar[Literal[1]] = 1
    UNREACH: ClassVar[Literal[2]] = 2

    prefill: DefaultValue[Literal[0, 1, 2]] = DefaultValue(0)
    """Value to pre-populate the form field with."""


@dataclass(frozen=True, kw_only=True)
class Integer(FormSpec[int]):
    """Specifies an input field for whole numbers.

    Consumer model:
    ***************
    **Type**: ``int``

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed as an extension to the input field."""
    unit_symbol: str = ""
    """Unit symbol to add to the input field."""
    prefill: Prefill[int] = InputHint(0)
    """Value to pre-populate the form field with."""


@dataclass(frozen=True, kw_only=True)
class MultilineText(FormSpec[str]):
    """Specifies a multiline text form.

    Consumer model:
    ***************
    **Type**: ``str``

    **Example**: Inputting "some text" in a MultilineText form would result
    in::

        "some text\\n"

    Arguments:
    **********
    """

    monospaced: bool = False
    """Display text in the form as monospaced."""
    macro_support: bool = False
    """Hint in the UI that macros can be used in the field.
    Replacing the macros in the plug-in is a responsibility of the plug-in developer."""
    label: Label | None = None
    """Text displayed in front of the input field."""
    prefill: Prefill[str] = InputHint("")
    """Value to pre-populate the form field with."""


@dataclass(frozen=True, kw_only=True)
class Percentage(FormSpec[float]):
    """Specifies an input field for percentages.

    Consumer model:
    ***************
    **Type**: ``float``

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed in front of the input field."""
    prefill: Prefill[float] = InputHint(0.0)
    """Value to pre-populate the form field with."""


class MatchingScope(Enum):
    PREFIX = auto()
    INFIX = auto()
    FULL = auto()


@dataclass(frozen=True, kw_only=True)
class RegularExpression(FormSpec[str]):
    """
    Specifies an input field for regular expressions.

    Consumer model:
    ***************
    **Type**: ``str``

    Arguments:
    **********
    """

    predefined_help_text: MatchingScope
    """Adds pre-formulated help text.
    For commonly used matching behavior you can choose from predefined help texts
    to describe how the pattern will be used to match.
    Implementing it in a way that fulfills this promise is a responsibility of the plug-in
    developer.
    """
    label: Label | None = None
    """Text displayed in front of the input field."""
    prefill: Prefill[str] = InputHint("")
    """Value to pre-populate the form field with."""


@dataclass(frozen=True, kw_only=True)
class ServiceState(FormSpec[Literal[0, 1, 2, 3]]):
    """Specifies the configuration of a service state.

    Consumer model:
    ***************
    **Type**: ``Literal[0, 1, 2, 3]``

    Example:
    ********

    >>> state_form_spec = ServiceState(
    ...     title=Title("State if something happens"),
    ...     prefill=DefaultValue(ServiceState.WARN),
    ... )

    Arguments:
    **********
    """

    OK: ClassVar[Literal[0]] = 0
    WARN: ClassVar[Literal[1]] = 1
    CRIT: ClassVar[Literal[2]] = 2
    UNKNOWN: ClassVar[Literal[3]] = 3

    prefill: DefaultValue[Literal[0, 1, 2, 3]] = DefaultValue(0)
    """Value to pre-populate the form field with."""


class FieldSize(Enum):
    SMALL = auto()
    MEDIUM = auto()
    LARGE = auto()


@dataclass(frozen=True, kw_only=True)
class String(FormSpec[str]):
    """
    Specifies an input field for single line text.

    Consumer model:
    ***************
    **Type**: ``str``

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed in front of the input field."""
    macro_support: bool = False
    """Hint in the UI that macros can be used in the field.
    Replacing the macros in the plug-in is a responsibility of the plug-in developer."""
    prefill: Prefill[str] = InputHint("")
    """Value to pre-populate the form field with."""
    field_size: FieldSize = FieldSize.MEDIUM
    """Size setting of the input field."""


class TimeMagnitude(Enum):
    MILLISECOND = auto()
    SECOND = auto()
    MINUTE = auto()
    HOUR = auto()
    DAY = auto()


@dataclass(frozen=True, kw_only=True)
class TimeSpan(FormSpec[float]):
    """Specifies an input field for time span.

    Consumer model:
    ***************
    **Type**: ``float``

    Example:
    ********

    >>> time_span_form_spec = TimeSpan(
    ...     title=Title("Time span"),
    ...     displayed_magnitudes=[TimeMagnitude.SECOND, TimeMagnitude.MINUTE],
    ...     prefill=DefaultValue(60.0),
    ... )

    The above example would allow the user to configure a time span by entering
    "3 minutes 20 seconds", resulting in a value of ``200.0``.

    Arguments:
    **********
    """

    label: Label | None = None
    """Text displayed as an extension to the input field."""
    displayed_magnitudes: Sequence[TimeMagnitude]
    """Magnitudes that can be entered in the UI.

    All of the listed magnitudes can be used to configure the desired time span, which will be the
    sum of the configured fields in seconds."""
    prefill: Prefill[float] = InputHint(0.0)
    """Value to pre-populate the form field with."""


class InvalidElementMode(Enum):
    KEEP = auto()
    COMPLAIN = auto()


@dataclass
class InvalidElementValidator:
    mode: InvalidElementMode = InvalidElementMode.COMPLAIN
    display: Title | None = None
    error_msg: Message | None = None


@dataclass(frozen=True)
class SingleChoiceElement:
    """Specifies an element of a single choice form.

    Arguments:
    **********
    """

    name: str
    """Identifier of the SingleChoiceElement. Must be a valid Python identifier."""
    title: Title
    """Human readable title that will be shown in the UI."""

    def __post_init__(self) -> None:
        if not self.name.isidentifier() or iskeyword(self.name):
            raise ValueError(f"'{self.name}' is not a valid, non-reserved Python identifier")


@dataclass(frozen=True, kw_only=True)
class SingleChoice(FormSpec[str]):
    """Specification for a (single-)selection from multiple options.

    Consumer model:
    ***************
    **Type**: ``str``

    Arguments:
    **********
    """

    elements: Sequence[SingleChoiceElement]
    """Elements to choose from."""
    no_elements_text: Message | None = None
    """Text to show if no elements are given."""
    frozen: bool = False
    """Set to `True` to prevent the value from being changed after initial configuration,
    e.g. for identifiers."""
    label: Label | None = None
    """Text displayed in front of the input field."""
    prefill: DefaultValue[str] | InputHint[Title] = InputHint(Title("Please choose"))
    """Pre-selected choice.

    If a DefaultValue is used, it must be one of the elements names.
    If an InputHint is used, its title will be shown as a placeholder in the input field, requiring
    the user to make a choice."""
    ignored_elements: tuple[str, ...] = ()
    """Elements that can not be configured, but aren't removed from rules if they are present.
    They might be ignored when rendering the ruleset.
    You can use these to deprecate elements, to avoid breaking the old configurations.
    """
    invalid_element_validation: InvalidElementValidator | None = None
    """Validate if the selected value is still offered as a choice."""

    def __post_init__(self) -> None:
        valid = {elem.name for elem in self.elements}
        if isinstance(self.prefill, DefaultValue) and self.prefill.value not in valid:
            raise ValueError(
                f"Invalid default: {self.prefill.value!r}, choose from {', '.join(valid)}"
            )
        if offenders := valid.intersection(self.ignored_elements):
            raise ValueError(
                f"Elements are marked as 'ignored' but still present: {', '.join(offenders)}"
            )
