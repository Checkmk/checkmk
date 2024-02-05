#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from dataclasses import dataclass
from enum import auto, Enum
from typing import Callable, ClassVar, Literal, Sequence

from .._localize import Localizable
from ._base import DefaultValue, FormSpec, InputHint, Migrate, Prefill


@dataclass(frozen=True, kw_only=True)
class BooleanChoice(FormSpec):
    """Specifies a form for configuring a choice between boolean values

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        prefill: Value to pre-populate the choice with.
        transform: Transformation of the stored configuration
    """

    label: Localizable | None = None
    prefill: DefaultValue[bool] = DefaultValue(False)
    transform: Migrate[bool] | None = None


class BinaryUnit(Enum):
    BYTE = auto()  # "Byte"
    KILOBYTE = auto()  # "KB"
    MEGABYTE = auto()  # "MB"
    GIGABYTE = auto()  # "GB"
    TERABYTE = auto()  # "TB"
    PETABYTE = auto()  # "PB"
    EXABYTE = auto()  # "EB"
    ZETTABYTE = auto()  # "ZB"
    YOTTABYTE = auto()  # "YB"
    KIBIBYTE = auto()  # "KiB"
    MEBIBYTE = auto()  # "MiB"
    GIBIBYTE = auto()  # "GiB"
    TEBIBYTE = auto()  # "TiB"
    PEBIBYTE = auto()  # "PiB"
    EXBIBYTE = auto()  # "EiB"
    ZEBIBYTE = auto()  # "ZiB"
    YOBIBYTE = auto()  # "YiB"


SI_BINARY_UNIT = (
    BinaryUnit.BYTE,
    BinaryUnit.KILOBYTE,
    BinaryUnit.MEGABYTE,
    BinaryUnit.GIGABYTE,
    BinaryUnit.TERABYTE,
)
IEC_BINARY_UNIT = (
    BinaryUnit.BYTE,
    BinaryUnit.KIBIBYTE,
    BinaryUnit.MEBIBYTE,
    BinaryUnit.GIBIBYTE,
    BinaryUnit.TEBIBYTE,
)


@dataclass(frozen=True, kw_only=True)
class DataSize(FormSpec):
    """Specifies an input field for data storage capacity

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        displayed_units: Units that can be selected in the UI
        prefill: Value in bytes to pre-populate the form field with.
        transform: Specify if/how the raw input value in bytes should be changed when loaded into
                   the form/saved from the form
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    label: Localizable | None = None
    displayed_units: Sequence[BinaryUnit] | None = None
    prefill: Prefill[int] = InputHint(0)

    transform: Migrate[int] | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True, kw_only=True)
class FileUpload(FormSpec):
    """Specifies a file upload form.

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        extensions: The extensions of the files to choose from. If set to `None`,
            all extensions are selectable.
        mime_types: The allowed mime types of uploaded files. If set to `None`,
            all mime types will be uploadable.
        custom_validate: Custom validation function.
            Will be executed in addition to any builtin validation logic.
            Needs to raise a ValidationError in case validation fails.
            The return value of the function will not be used.

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

    custom_validate: Callable[[tuple[str, str, bytes]], object] | None = None


@dataclass(frozen=True, kw_only=True)
class FixedValue(FormSpec):
    """
    Specifies a fixed non-editable value

    Can be used in a CascadingSingleChoice and Dictionary to represent a fixed value option.

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        value: Atomic value produced by the form spec
        label: Text displayed underneath the title
        transform: Transformation of the stored configuration
    """

    value: int | float | str | bool | None
    label: Localizable | None = None

    transform: Migrate[int | float | str | bool | None] | None = None

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
class Float(FormSpec):
    """Specifies an input field for floating point numbers

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
        display_precision: How many decimal places to display
        prefill: Value to pre-populate the form field with.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    label: Localizable | None = None
    unit: Localizable | None = None
    display_precision: int | None = None

    prefill: Prefill[float] = InputHint(0.0)

    transform: Migrate[float] | None = None

    custom_validate: Callable[[float], object] | None = None


@dataclass(frozen=True, kw_only=True)
class HostState(FormSpec):
    """Specifies the configuration of a host state.

    >>> state_form_spec = HostState(
    ...     title=Localizable("Host state"),
    ...     prefill=DefaultValue(HostState.UP),
    ... )
    """

    UP: ClassVar[Literal[0]] = 0
    DOWN: ClassVar[Literal[1]] = 1
    UNREACH: ClassVar[Literal[2]] = 2

    prefill: DefaultValue[Literal[0, 1, 2]] = DefaultValue(0)

    transform: Migrate[Literal[0, 1, 2]] | None = None


@dataclass(frozen=True, kw_only=True)
class Integer(FormSpec):
    """Specifies an input field for whole numbers

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
        prefill: Value to pre-populate the form field with.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.

    Consumer model:
        **Type**: ``int``

        The configured value will be presented as an integer to consumers.
    """

    label: Localizable | None = None
    unit: Localizable | None = None
    prefill: Prefill[int] = InputHint(0)

    transform: Migrate[int] | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True, kw_only=True)
class MultilineText(FormSpec):
    """Specifies a multiline text form

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        monospaced: Display text in the form as monospaced
        label: Text displayed in front of the input field
        prefill: Value to pre-populate the form field with.
        transform: Transformation of the stored configuration
        custom_validate: Custom validation function.
            Will be executed in addition to any builtin validation logic.
            Needs to raise a ValidationError in case validation fails.
            The return value of the function will not be used.

    Consumer model:
        **Type**: ``str``

        The configured value will be presented as a string.

        **Example**: Inputting "some text" in a MultilineText form would result
        in::

            "some text\\n"
    """

    monospaced: bool = False

    label: Localizable | None = None

    prefill: Prefill[str] = InputHint("")
    transform: Migrate[str] | None = None
    custom_validate: Callable[[str], object] | None = None


@dataclass(frozen=True, kw_only=True)
class Percentage(FormSpec):
    """Specifies an input field for percentages

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed in front of the input field
        display_precision: How many decimal places to display
        prefill: Value to pre-populate the form field with.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    label: Localizable | None = None
    display_precision: int | None = None

    prefill: Prefill[float] = InputHint(0.0)

    transform: Migrate[float] | None = None

    custom_validate: Callable[[float], object] | None = None


class MatchingScope(Enum):
    PREFIX = auto()
    INFIX = auto()
    FULL = auto()


@dataclass(frozen=True, kw_only=True)
class RegularExpression(FormSpec):
    """
    Specifies an input field for regular expressions

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        predefined_help_text: Adds pre-formulated help text on how the pattern will be used to match
                              for commonly used matching behavior.
        label: Text displayed as an extension to the input field
        prefill: Value to pre-populate the form field with.
        transform: Transformation of the stored configuration
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    predefined_help_text: MatchingScope
    label: Localizable | None = None

    prefill: Prefill[str] = InputHint("")

    transform: Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None


@dataclass(frozen=True, kw_only=True)
class ServiceState(FormSpec):
    """Specifies the configuration of a service state.

    >>> state_form_spec = ServiceState(
    ...     title=Localizable("State if somthing happens"),
    ...     prefill=DefaultValue(ServiceState.WARN),
    ... )
    """

    OK: ClassVar[Literal[0]] = 0
    WARN: ClassVar[Literal[1]] = 1
    CRIT: ClassVar[Literal[2]] = 2
    UNKNOWN: ClassVar[Literal[3]] = 3

    prefill: DefaultValue[Literal[0, 1, 2, 3]] = DefaultValue(0)

    transform: Migrate[Literal[0, 1, 2, 3]] | None = None


@dataclass(frozen=True, kw_only=True)
class Text(FormSpec):
    """
    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed in front of the input field
        prefill: Value to pre-populate the form field with.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    label: Localizable | None = None

    prefill: Prefill[str] = InputHint("")

    transform: Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None


class TimeUnit(Enum):
    MILLISECOND = auto()  # "milliseconds"
    SECOND = auto()  # "seconds"
    MINUTE = auto()  # "minutes"
    HOUR = auto()  # "hours"
    DAY = auto()  # "days"


@dataclass(frozen=True, kw_only=True)
class TimeSpan(FormSpec):
    """Specifies an input field for time span

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        displayed_units: Units that can be configured in the UI. All of the listed units can be
                        configured and the value is the sum of the configured fields in seconds.
        prefill: Value in seconds to pre-populate the form fields with.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.

    Consumer model:
        **Type**: ``float``

        The configured value will be presented as a float to consumers.
    """

    label: Localizable | None = None
    displayed_units: Sequence[TimeUnit] | None = None
    prefill: Prefill[float] = InputHint(0.0)
    transform: Migrate[Sequence[float]] | None = None
    custom_validate: Callable[[float], object] | None = None


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
class SingleChoice(FormSpec):
    """Specification for a (single-)selection from multiple options

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        elements: Elements to choose from
        no_elements_text: Text to show if no elements are given
        frozen: If the value can be changed after initial configuration, e.g. for identifiers
        label: Text displayed in front of the input field
        prefill: Pre-selected choice. Must be one of the elements names.
        deprecated_elements: Elements that can still be present in stored user configurations, but
                             are no longer offered
        invalid_element_validation: Validate if the selected value is still offered as a choice
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    elements: Sequence[SingleChoiceElement]
    no_elements_text: Localizable | None = None

    frozen: bool = False

    label: Localizable | None = None

    prefill: DefaultValue[str] | InputHint[Localizable] = InputHint(Localizable("Please choose"))

    deprecated_elements: tuple[str, ...] | None = None
    invalid_element_validation: InvalidElementValidator | None = None
    transform: Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None

    def __post_init__(self) -> None:
        valid = {elem.name for elem in self.elements}
        if isinstance(self.prefill, DefaultValue) and self.prefill.value not in valid:
            raise ValueError(
                f"Invalid default: {self.prefill.value!r}, choose from {', '.join(valid)}"
            )
