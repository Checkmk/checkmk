#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Generic, Literal, TypeVar

from ._localize import Localizable
from .preconfigured import Metric, Proxy

_T = TypeVar("_T")


@dataclass(frozen=True)
class Migrate(Generic[_T]):
    """Creates a transformation that changes the value as a one-off event.

    You can add a ``Migrate`` instance to a form spec to update the value from an
    old version to be compatible with the current definition.

    Args:
        model_to_form: Transforms the present parameter value ("consumer model")
                       to a value compatible with the current form specification.
    """

    model_to_form: Callable[[object], _T]


@dataclass(frozen=True)
class Transform(Generic[_T]):
    """Creates a transformation that is performed every time the value is loaded/stored.

    E.g. could be used to allow a different unit to be shown/entered than that is used by
    the consumers of the stored value.

    Args:
        model_to_form: Transforms the value presented to the consumers ("consumer model")
                       to a value compatible with the current form specification.
        form_to_model: Transforms the value created by the form specification to the
                        value presented to the consumers (e.g. check plugins).
    """

    model_to_form: Callable[[object], _T]
    form_to_model: Callable[[_T], object]


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

    Consumer model:
        **Type**: ``int``

        The configured value will be presented as an integer to consumers.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None
    unit: Localizable | None = None
    prefill_value: int | None = None

    transform: Transform[int] | Migrate[int] | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True)
class Float:
    """Specifies an input field for floating point numbers

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        unit: Unit of the input (only for display)
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
    unit: Localizable | None = None
    display_precision: int | None = None

    prefill_value: float | None = None

    transform: Transform[float] | Migrate[float] | None = None

    custom_validate: Callable[[float], object] | None = None


@dataclass(frozen=True)
class DataSize:
    """Specifies an input field for data storage capacity

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        prefill_value: Value in bytes to pre-populate the form field with. If None, the backend will
                       decide whether to leave the field empty or to prefill it with a canonical
                       value.
        transform: Specify if/how the raw input value in bytes should be changed when loaded into
                   the form/saved from the form
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None
    prefill_value: int | None = None

    transform: Transform[int] | Migrate[int] | None = None

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

    transform: Transform[float] | Migrate[float] | None = None

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

    transform: Transform[str] | Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None


@dataclass(frozen=True)
class Tuple:
    elements: Sequence["FormSpec"]

    title: Localizable | None = None
    help_text: Localizable | None = None

    transform: Transform[tuple[object, ...]] | Migrate[tuple[object, ...]] | None = None

    custom_validate: Callable[[tuple[object, ...]], object] | None = None


class InvalidElementMode(enum.Enum):
    KEEP = enum.auto()
    COMPLAIN = enum.auto()


@dataclass
class InvalidElementValidator:
    mode: InvalidElementMode = InvalidElementMode.COMPLAIN
    display: Localizable | None = None
    error_msg: Localizable | None = None


@dataclass(frozen=True)
class DropdownChoiceElement:
    name: str
    title: Localizable


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

    prefill_selection: str | None = None

    deprecated_elements: tuple[str, ...] | None = None
    invalid_element_validation: InvalidElementValidator | None = None
    transform: Transform[str] | Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None


@dataclass(frozen=True)
class CascadingDropdownElement:
    name: str
    title: Localizable
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
        transform: Tranformations to appy.

    Consumer model:
        **Type**: ``tuple[str, object]``

        The configured value will be presented as a 2-tuple consisting of the name of the choice and
        the consumer model of the selected form specification.

        **Example**: A CascadingDropdown with a selcted :class:`Dictionary` form specification would
        result in ``("my_value", {...})``
    """

    elements: Sequence[CascadingDropdownElement]

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None

    prefill_selection: str | None = None

    transform: Transform[object] | Migrate[object] | None = None

    def __post_init__(self) -> None:
        avail_idents = [elem.name for elem in self.elements]
        if self.prefill_selection is not None and self.prefill_selection not in avail_idents:
            raise ValueError("Default element is not one of the specified elements")


@dataclass(frozen=True)
class DictElement:
    """
    Args:
        parameter_form: Configuration specification of this entry
        required: Whether the user has to configure the value in question. If set to False, it may
                  be omitted.
        read_only: Element that can't be edited. Can be used to store the discovered parameters.
    """

    parameter_form: "FormSpec"
    required: bool | None = False
    read_only: bool | None = False


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

    no_elements_text: Localizable | None = None

    deprecated_elements: tuple[str, ...] = field(default_factory=tuple)
    transform: Transform[Mapping[str, object]] | Migrate[Mapping[str, object]] | None = None

    custom_validate: Callable[[Mapping[str, object]], object] | None = None

    def __post_init__(self) -> None:
        for key in self.elements.keys():
            assert key.isidentifier(), f"'{key}' is not a valid python identifier"


@dataclass(frozen=True)
class ServiceState:
    """Specifies the configuration of a service state.

    >>> state_form_spec = ServiceState(
    ...     title=Localizable("State if somthing happens"),
    ...     prefill_value=ServiceState.WARN,
    ... )
    """

    OK: ClassVar[Literal[0]] = 0
    WARN: ClassVar[Literal[1]] = 1
    CRIT: ClassVar[Literal[2]] = 2
    UNKNOWN: ClassVar[Literal[3]] = 3

    title: Localizable | None = None
    help_text: Localizable | None = None

    prefill_value: Literal[0, 1, 2, 3] = 0

    transform: Transform[Literal[0, 1, 2, 3]] | Migrate[Literal[0, 1, 2, 3]] | None = None


@dataclass(frozen=True)
class HostState:
    """Specifies the configuration of a host state.

    >>> state_form_spec = HostState(
    ...     title=Localizable("Host state"),
    ...     prefill_value=HostState.UP,
    ... )
    """

    UP: ClassVar[Literal[0]] = 0
    DOWN: ClassVar[Literal[1]] = 1
    UNREACH: ClassVar[Literal[2]] = 2

    title: Localizable | None = None
    help_text: Localizable | None = None

    prefill_value: Literal[0, 1, 2] = 0

    transform: Transform[Literal[0, 1, 2]] | Migrate[Literal[0, 1, 2]] | None = None


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
    order_editable: bool = True

    prefill_value: Sequence[object] | None = None
    transform: Transform[Sequence[object]] | Migrate[Sequence[object]] | None = None
    custom_validate: Callable[[Sequence[object]], object] | None = None


@dataclass(frozen=True)
class FixedValue:
    """
    Specifies a fixed non-editable value

    Can be used in a CascadingDropdown and Dictionary to represent a fixed value option.

    Args:
        value: Atomic value produced by the form spec
        title: Human readable title
        label: Text displayed underneath the title
        help_text: Description to help the user with the configuration
    """

    value: int | float | str | bool | None
    title: Localizable | None = None
    label: Localizable | None = None
    help_text: Localizable | None = None

    transform: Transform[Sequence[int | float | str | bool | None]] | Migrate[
        Sequence[int | float | str | bool | None]
    ] | None = None

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


class DisplayUnits(enum.Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


@dataclass(frozen=True)
class TimeSpan:
    """Specifies an input field for time span

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        displayed_units: Units that can be configured in the UI. All of the listed units can be
                        configured and the value is the sum of the configured fields in seconds.
        prefill_value: Value in seconds to pre-populate the form fields with. If None, the backend
                        will decide whether to leave the field empty or to prefill it with
                        a canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    title: Localizable | None = None
    help_text: Localizable | None = None
    label: Localizable | None = None
    displayed_units: Sequence[DisplayUnits] | None = None
    prefill_value: int | None = None
    transform: Transform[Sequence[int]] | Migrate[Sequence[int]] | None = None
    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True)
class FixedLevels:
    """Definition for levels that remain static. Usable only in conjunction with `Levels`

    Args:
        prefill_value: Value to pre-populate the form fields with. If None, the backend will decide
                       whether to leave the field empty or to prefill it with a canonical value.
    """

    prefill_value: tuple[float, float] | None = None


@dataclass(frozen=True)
class PredictiveLevels:
    """Definition for levels that change over time based on a prediction of the monitored value.
    Usable only in conjunction with `Levels`

    Args:
        prefill_abs_diff: Value to pre-populate the form fields with when the levels depend on the
         absolute difference to the predicted value. If None, the backend will decide whether to
         leave the field empty or to prefill it with a canonical value.
        prefill_rel_diff: Value to pre-populate the form fields with when the levels depend on the
         relative difference to the predicted value. If None, the backend will decide whether to
         leave the field empty or to prefill it with a canonical value.
        prefill_stddev_diff: Value to pre-populate the form fields with when the levels depend on
         the relation of the predicted value to the standard deviation. If None, the backend will
         decide whether to leave the field empty or to prefill it with a canonical value.
    """

    prefill_abs_diff: tuple[float, float] | None = None
    prefill_rel_diff: tuple[float, float] | None = None
    prefill_stddev_diff: tuple[float, float] | None = None


@dataclass(frozen=True)
class Levels:
    """Specifies a form for configuring levels

    Args:
        form_spec: Specification for the form fields of the warning and critical levels
        lower: Lower levels
        upper: Upper levels
        title: Human readable title
        help_text: Description to help the user with the configuration
        unit: Unit of the value to apply levels on (only for display)
        transform: Transformation of the stored configuration

    Consumer model:
        **Type**:
          This is the type definition of
          the consumer model::
            class LevelsConsumerModel(TypedDict):
                levels_lower: _NoLevels | _FixedLevels | _PredictiveLevels
                levels_upper: _NoLevels | _FixedLevels | _PredictiveLevels

          where the tree possible types are defined
          as follows::
            _NoLevels = tuple[Literal["no_levels"], None]

            _FixedLevels = tuple[Literal["fixed"], tuple[int | int] | tuple[float, float]]

            _PredictiveLevels = tuple[Literal["predictive"], _PredictiveModel]

            class _PredictiveModel(TypedDict):
                period: Literal["wday", "day", "hour", "minute"]
                horizon: int
                levels: tuple[
                    Literal["absolute", "relative", "stddev"],
                    tuple[int, int] | tuple[float, float],
                ]
                bound: tuple[int, int] | tuple[float, float]
                __get_predictive_levels__: Callable | None


          The configured value will be presented to consumers as a nested dictionary
          with the two keys "levels_lower" and "levers_upper" always present.

        **Example**:
            Levels used to configure no levels will look
            like this::
                {
                    "levels_lower": ("no_levels", None),
                    "levels_upper": ("no_levels", None),
                }

            Levels used to configure fixed lower levels might look
            like this::
                {
                    "levels_lower": ("fixed", (5.0, 1.0)),
                    "levels_upper": ("no_levels", None),
                }

            Levels used to configure upper predictive levels might look
            like this::
                {
                    "levels_lower": ("no_levels", None),
                    "levels_upper": (
                        "predictive",
                        {
                            "period": "hour",
                            "horizon": 90,
                            "levels": ("stddev", (2.0, 4.0)),
                            "bound": (23.0, 42.0),
                            __get_predictive_levels__: None,
                        },
                    ),
                }


    """

    form_spec: type[Integer | Float | DataSize | Percentage]  # TODO: any numeric FormSpec
    lower: tuple[FixedLevels, PredictiveLevels | None] | None
    upper: tuple[FixedLevels, PredictiveLevels | None] | None

    title: Localizable | None = None
    help_text: Localizable | None = None
    unit: Localizable | None = None

    transform: Transform[object] | Migrate[object] | None = None


@dataclass(frozen=True)
class BooleanChoice:
    """Specifies a form for configuring a choice between boolean values

    Args:
        label: Text displayed as an extension to the input field
        title: Human readable title
        help_text: Description to help the user with the configuration
        prefill_value: Boolean value to pre-populate the form fields with. If None, the backend
            will decide whether to leave the field empty or to prefill it with
            a canonical value.
        transform: Transformation of the stored configuration
    """

    label: Localizable | None = None
    title: Localizable | None = None
    help_text: Localizable | None = None
    prefill_value: bool | None = None
    transform: Transform[bool] | Migrate[bool] | None = None


@dataclass(frozen=True)
class FileUpload:
    """Specifies a file upload form.

    Args:
        extensions: The extensions of the files to choose from.
        mime_types: The allowed mime types of uploaded files.
        title: Human readable title.
        help_text: Description to help the user with the configuration
        custom_validate: Custom validation function. Will be executed in addition to any
         builtin validation logic. Needs to raise a ValidationError in case
        validation fails. The return value of the function will not be used.

    Consumer model:
        **Type**:
            ``tuple[str, str, bytes]``

            The configured value will be presented as a 3-tuple consisting of the name of
            the uploaded file, its mime type, and the files content as bytes.

        **Example**:
          Choosing a pem file to upload would result
          in::
            (
                "my_cert.pem",
                "application/octet-stream",
                b"-----BEGIN CERTIFICATE-----\\n....",
            )

    """

    extensions: tuple[str, ...] | None = None
    mime_types: tuple[str, ...] | None = None

    title: Localizable | None = None
    help_text: Localizable | None = None

    custom_validate: Callable[[tuple[str, str, bytes]], object] | None = None


ItemFormSpec = TextInput | DropdownChoice


FormSpec = (
    Integer
    | Float
    | DataSize
    | Percentage
    | TextInput
    | Tuple
    | DropdownChoice
    | CascadingDropdown
    | Dictionary
    | ServiceState
    | HostState
    | List
    | FixedValue
    | TimeSpan
    | Levels
    | Proxy
    | BooleanChoice
    | FileUpload
    | Metric
)
