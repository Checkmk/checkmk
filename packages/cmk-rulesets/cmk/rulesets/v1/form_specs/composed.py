#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""FormSpecs that can be composed of other FormSpecs"""

from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from .._localize import Localizable
from ._base import FormSpec, Migrate


@dataclass(frozen=True, kw_only=True)
class TupleDoNotUseWillbeRemoved(FormSpec):
    elements: Sequence[FormSpec]

    transform: Migrate[tuple[object, ...]] | None = None

    custom_validate: Callable[[tuple[object, ...]], object] | None = None


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
