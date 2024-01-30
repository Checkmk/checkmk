#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import enum
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Generic, Literal, TypeVar

from ._base import FormSpec
from ._localize import Localizable

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


@dataclass(frozen=True, kw_only=True)
class Integer(FormSpec):
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

    label: Localizable | None = None
    unit: Localizable | None = None
    prefill_value: int | None = None

    transform: Migrate[int] | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True, kw_only=True)
class Float(FormSpec):
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

    label: Localizable | None = None
    unit: Localizable | None = None
    display_precision: int | None = None

    prefill_value: float | None = None

    transform: Migrate[float] | None = None

    custom_validate: Callable[[float], object] | None = None


class BinaryUnit(enum.Enum):
    BYTE = "Byte"
    KILOBYTE = "KB"
    MEGABYTE = "MB"
    GIGABYTE = "GB"
    TERABYTE = "TB"
    PETABYTE = "PB"
    EXABYTE = "EB"
    ZETTABYTE = "ZB"
    YOTTABYTES = "YB"
    KIBIBYTE = "KiB"
    MEBIBYTE = "MiB"
    GIBIBYTE = "GiB"
    TEBIBYTE = "TiB"
    PEBIBYTE = "PiB"
    EXBIBYTE = "EiB"
    ZEBIBYTE = "ZiB"
    YOBIBYTE = "YiB"


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
        prefill_value: Value in bytes to pre-populate the form field with. If None, the backend will
                       decide whether to leave the field empty or to prefill it with a canonical
                       value.
        transform: Specify if/how the raw input value in bytes should be changed when loaded into
                   the form/saved from the form
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    label: Localizable | None = None
    displayed_units: Sequence[BinaryUnit] | None = None
    prefill_value: int | None = None

    transform: Migrate[int] | None = None

    custom_validate: Callable[[int], object] | None = None


@dataclass(frozen=True, kw_only=True)
class Percentage(FormSpec):
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

    label: Localizable | None = None

    display_precision: int | None = None

    prefill_value: float | None = None

    transform: Migrate[float] | None = None

    custom_validate: Callable[[float], object] | None = None


@dataclass(frozen=True, kw_only=True)
class Text(FormSpec):
    """
    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed in front of the input field
        input_hint: A short hint to aid the user with data entry (e.g. an example)
        prefill_value: Value to pre-populate the form field with. If None, the backend will decide
                       whether to leave the field empty or to prefill it with a canonical value.
        custom_validate: Custom validation function. Will be executed in addition to any
                         builtin validation logic. Needs to raise a ValidationError in case
                         validation fails. The return value of the function will not be used.
    """

    label: Localizable | None = None
    input_hint: str | None = None

    prefill_value: str | None = None

    transform: Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None


@dataclass(frozen=True, kw_only=True)
class TupleDoNotUseWillbeRemoved(FormSpec):
    elements: Sequence[FormSpec]

    transform: Migrate[tuple[object, ...]] | None = None

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
        prefill_selection: Pre-selected choice.
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

    prefill_selection: str | None = None

    deprecated_elements: tuple[str, ...] | None = None
    invalid_element_validation: InvalidElementValidator | None = None
    transform: Migrate[str] | None = None

    custom_validate: Callable[[str], object] | None = None

    def __post_init__(self) -> None:
        avail_idents = [elem.name for elem in self.elements]
        if self.prefill_selection is not None and self.prefill_selection not in avail_idents:
            raise ValueError("Default element is not one of the specified elements")


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceElement:
    """Specifies an element of a single choice cascading form

    Args:
        name: Identifier of the CascadingSingleChoiceElement. Must be a valid Python identifier.
        title: Human readable title that will be shown in the UI
    """

    name: str
    title: Localizable
    parameter_form: FormSpec

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"'{self.name}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoice(FormSpec):
    """Specification for a single-selection from multiple options. Selection is another spec

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        elements: Elements to choose from
        label: Text displayed in front of the input field
        prefill_selection: Name of pre-selected choice. If not set, the user is required to make a
                           selection
        transform: Transformations to apply.

    Consumer model:
        **Type**: ``tuple[str, object]``

        The configured value will be presented as a 2-tuple consisting of the name of the choice and
        the consumer model of the selected form specification.

        **Example**: A CascadingSingleChoice with a selected :class:`Dictionary` form specification
        would result in ``("my_value", {...})``
    """

    elements: Sequence[CascadingSingleChoiceElement]

    label: Localizable | None = None

    prefill_selection: str | None = None

    transform: Migrate[tuple[str, object]] | None = None

    def __post_init__(self) -> None:
        avail_idents = [elem.name for elem in self.elements]
        if self.prefill_selection is not None and self.prefill_selection not in avail_idents:
            raise ValueError("Default element is not one of the specified elements")


@dataclass(frozen=True, kw_only=True)
class DictElement:
    """Specifies an element of a dictionary form

    Args:
        parameter_form: Configuration specification of this entry
        required: Whether the user has to configure the value in question. If set to False, it may
                  be omitted.
        read_only: Element that can't be edited. Can be used to store the discovered parameters.
    """

    parameter_form: FormSpec
    required: bool = False
    read_only: bool = False


@dataclass(frozen=True, kw_only=True)
class Dictionary(FormSpec):
    """
    Specifies a (multi-)selection of configuration options.

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        elements: key-value mapping where the key identifies the selected option and the value
                  specifies how the option can be configured. The key has to be a valid Python
                  identifier.
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

    no_elements_text: Localizable | None = None

    deprecated_elements: tuple[str, ...] = field(default_factory=tuple)
    transform: Migrate[Mapping[str, object]] | None = None

    custom_validate: Callable[[Mapping[str, object]], object] | None = None

    def __post_init__(self) -> None:
        for key in self.elements:
            if not key.isidentifier():
                raise ValueError(f"'{key}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)
class ServiceState(FormSpec):
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

    prefill_value: Literal[0, 1, 2, 3] = 0

    transform: Migrate[Literal[0, 1, 2, 3]] | None = None


@dataclass(frozen=True, kw_only=True)
class HostState(FormSpec):
    """Specifies the configuration of a host state.

    >>> state_form_spec = HostState(
    ...     title=Localizable("Host state"),
    ...     prefill_value=HostState.UP,
    ... )
    """

    UP: ClassVar[Literal[0]] = 0
    DOWN: ClassVar[Literal[1]] = 1
    UNREACH: ClassVar[Literal[2]] = 2

    prefill_value: Literal[0, 1, 2] = 0

    transform: Migrate[Literal[0, 1, 2]] | None = None


@dataclass(frozen=True, kw_only=True)
class List(FormSpec):
    """
    Specifies a list of configuration elements of the same type.

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        parameter_form: Configuration specification of the list elements
        custom_validate: Custom validation function. Will be executed in addition to any
            builtin validation logic. Needs to raise a ValidationError in case
            validation fails. The return value of the function will not be used.
        prefill_value: Value to pre-populate the form field with
        order_editable: Can the elements be reordered in the UI
        add_element_label: Label used to customize the add element button. If not set,
            the default label will be used.
        remove_element_label: Label used to customize the remove element button. If not set,
            the default label will be used.
        list_empty_label: Label used in the rule summary if the list is empty.
    """

    parameter_form: FormSpec
    order_editable: bool = True
    add_element_label: Localizable | None = None
    remove_element_label: Localizable | None = None
    list_empty_label: Localizable | None = None

    prefill_value: Sequence[object] | None = None
    transform: Migrate[Sequence[object]] | None = None
    custom_validate: Callable[[Sequence[object]], object] | None = None


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


class TimeUnit(enum.Enum):
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


@dataclass(frozen=True, kw_only=True)
class TimeSpan(FormSpec):
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

    Consumer model:
        **Type**: ``float``

        The configured value will be presented as a float to consumers.
    """

    label: Localizable | None = None
    displayed_units: Sequence[TimeUnit] | None = None
    prefill_value: float | None = None
    transform: Migrate[Sequence[float]] | None = None
    custom_validate: Callable[[float], object] | None = None


@dataclass(frozen=True, kw_only=True)
class PredictiveLevels:
    """Definition for levels that change over time based on a prediction of the monitored value.
    Usable only in conjunction with `Levels`

    Args:
        reference_metric: The name of the metric that should be used to compute the prediction.
         This value is hardcoded by you, the developer. It is your responsibility to make sure
         that all plugins subscribing to the ruleset actually create this metric.
         Failing to do so will prevent the backend from providing a prediction, currently leading
         to an always OK service.
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

    reference_metric: str
    prefill_abs_diff: tuple[float, float] | None = None
    prefill_rel_diff: tuple[float, float] | None = None
    prefill_stddev_diff: tuple[float, float] | None = None


class LevelDirection(enum.Enum):
    """Specifies a type of bound the levels represents"""

    UPPER = "upper"
    LOWER = "lower"


@dataclass(frozen=True, kw_only=True)
class Levels(FormSpec):
    """Specifies a form for configuring levels

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        form_spec_template: Template for the specification of the form fields of the warning and
            critical levels. If `title` or `prefill_value` are provided here, they will be ignored
        level_direction: Do the levels represent the lower or the upper bound.
            It's used only to provide labels and error messages in the UI.
        predictive: Specification for the predictive levels
        prefill_fixed_levels: Value to pre-populate the form fields of fixed levels with.
            If None, the backend will decide whether to leave the field empty or to prefill it
            with a canonical value.
        transform: Transformation of the stored configuration

    Consumer model:
        **Type**: ``_NoLevels | _FixedLevels | _PredictiveLevels``

        The value presented to consumers will be crafted in a way that makes it a suitable
        argument for the ``check_levels`` function of the agent based API.
        These are the tree possible types defined in the consumer model::

          _NoLevels = tuple[
              Literal["no_levels"],
              None,
          ]

          _FixedLevels = tuple[
              Literal["fixed"],
              # (warn, crit)
              tuple[int, int] | tuple[float, float],
          ]

          _PredictiveLevels = tuple[
              Literal["predictive"],
              # (reference_metric, predicted_value, levels_tuple)
              tuple[str, float | None, tuple[float, float] | None],
          ]

        The configured value will be presented to consumers as a 2-tuple consisting of
        level type identifier and one of the 3 types: None, 2-tuple of numbers or a
        3-tuple containing the name of the reference metric used for prediction,
        the predicted value and the resulting levels tuple.

        **Example**: Levels used to configure no levels will look
        like this::

            ("no_levels", None)

        Levels used to configure fixed lower levels might look
        like this::

            ("fixed", (5.0, 1.0))

        Levels resulting from configured upper predictive levels might look
        like this::

            ("predictive", ("mem_used_percent", 42.1, (50.3, 60.7)))

    """

    form_spec_template: DataSize | Float | Integer | Percentage | TimeSpan
    level_direction: LevelDirection
    predictive: PredictiveLevels | None

    prefill_fixed_levels: tuple[float, float] | None = None

    transform: Migrate[object] | None = None


@dataclass(frozen=True, kw_only=True)
class BooleanChoice(FormSpec):
    """Specifies a form for configuring a choice between boolean values

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        label: Text displayed as an extension to the input field
        prefill_value: Boolean value to pre-populate the choice with.
        transform: Transformation of the stored configuration
    """

    label: Localizable | None = None
    prefill_value: bool = False
    transform: Migrate[bool] | None = None


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
class MultipleChoiceElement:
    """Specifies an element of a multiple choice form

    Args:
        name: Identifier of the MultipleChoiceElement. Must be a valid Python identifier.
        title: Human readable title that will be shown in the UI
    """

    name: str
    title: Localizable

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"'{self.name}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)
class MultipleChoice(FormSpec):
    """Specifies a multiple choice form

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        elements: Elements to choose from
        show_toggle_all: Show toggle all elements option in the UI
        prefill_selections: List of element names to check by default. If None, the backend
            will decide whether to leave the selection empty or to prefill it with
            a canonical value.
        transform: Transformation of the stored configuration
        custom_validate: Custom validation function. Will be executed in addition to any
            builtin validation logic. Needs to raise a ValidationError in case
            validation fails. The return value of the function will not be used.

    Consumer model:
        **Type**: ``list[str]``

        The configured value will be presented as a list consisting of the names
        of the selected elements.

        **Example**: MultipleChoice with two selected elements would result
        in::

            ["choice1", "choice2"]

    """

    elements: Sequence[MultipleChoiceElement]
    show_toggle_all: bool = False

    prefill_selections: Sequence[str] = ()
    transform: Migrate[Sequence[str]] | None = None
    custom_validate: Callable[[Sequence[str]], object] | None = None

    def __post_init__(self) -> None:
        avail_idents = {elem.name for elem in self.elements}
        if invalid := {ident for ident in self.prefill_selections if ident not in avail_idents}:
            raise ValueError(f"Invalid prefill element(s): {', '.join(invalid)}")


@dataclass(frozen=True, kw_only=True)
class MultilineText(FormSpec):
    """Specifies a multiline text form

    Args:
        title: Human readable title
        help_text: Description to help the user with the configuration
        monospaced: Display text in the form as monospaced
        label: Text displayed in front of the input field
        prefill_value: Value to pre-populate the form field with.
            If None, the backend will decide whether to leave the field
            empty or to prefill it with a canonical value.
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

    prefill_value: str | None = None
    transform: Migrate[str] | None = None
    custom_validate: Callable[[str], object] | None = None


ItemFormSpec = Text | SingleChoice
