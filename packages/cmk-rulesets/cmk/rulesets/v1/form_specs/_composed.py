#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""FormSpecs that can be composed of other FormSpecs"""

from dataclasses import dataclass
from typing import Any, Generic, Mapping, Sequence

from .._localize import Label, Message, Title
from ._base import DefaultValue, FormSpec, InputHint, ModelT


@dataclass(frozen=True, kw_only=True)  # type: ignore[misc]
class TupleDoNotUseWillbeRemoved(FormSpec[tuple[object, ...]]):
    elements: Sequence[FormSpec[Any]]


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceElement(Generic[ModelT]):
    """Specifies an element of a single choice cascading form

    Args:
        name: Identifier of the CascadingSingleChoiceElement. Must be a valid Python identifier.
        title: Human readable title that will be shown in the UI
    """

    name: str
    title: Title
    parameter_form: FormSpec[ModelT]

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"'{self.name}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)  # type: ignore[misc]
class CascadingSingleChoice(FormSpec[tuple[str, object]]):
    """Specification for a single-selection from multiple options. Selection is another spec

    Args:
        elements: Elements to choose from
        label: Text displayed in front of the input field
        prefill: Name of pre-selected choice. Must be one of the elements names.

    Consumer model:
        **Type**: ``tuple[str, object]``

        The configured value will be presented as a 2-tuple consisting of the name of the choice and
        the consumer model of the selected form specification.

        **Example**: A CascadingSingleChoice with a selected :class:`Dictionary` form specification
        would result in ``("my_value", {...})``
    """

    elements: Sequence[CascadingSingleChoiceElement[Any]]
    label: Label | None = None

    prefill: DefaultValue[str] | InputHint[Title] = InputHint(Title("Please choose"))

    def __post_init__(self) -> None:
        avail_idents = {elem.name for elem in self.elements}  # type: ignore[misc]
        if isinstance(self.prefill, DefaultValue) and self.prefill.value not in avail_idents:
            raise ValueError("Default element is not one of the specified elements")


@dataclass(frozen=True, kw_only=True)
class DictElement(Generic[ModelT]):
    """Specifies an element of a dictionary form

    Args:
        parameter_form: Configuration specification of this entry
        required: Whether the user has to configure the value in question. If set to False, it may
                  be omitted.
        render_only: Element that can't be edited. Can be used to store the discovered parameters.
    """

    parameter_form: FormSpec[ModelT]
    required: bool = False
    render_only: bool = False


@dataclass(frozen=True, kw_only=True)  # type: ignore[misc]
class Dictionary(FormSpec[Mapping[str, object]]):
    """
    Specifies a (multi-)selection of configuration options.

    Args:
        elements: key-value mapping where the key identifies the selected option and the value
                  specifies how the option can be configured. The key has to be a valid Python
                  identifier.
        deprecated_elements: Elements that can no longer be configured, but aren't removed
                            from the old rules that already have them configured. Can be
                            used when deprecating elements, to avoid breaking the old
                            configurations.
                            They are configured with a list of element keys.
        no_elements_text: Text to show if no elements are specified
    """

    elements: Mapping[str, DictElement[Any]]

    no_elements_text: Message = Message("(no parameters)")

    deprecated_elements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for key in self.elements:  # type: ignore[misc]
            if not key.isidentifier():
                raise ValueError(f"'{key}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)
class List(FormSpec[Sequence[ModelT]]):
    """
    Specifies a list of configuration elements of the same type.

    Args:
        element_template: Configuration specification of the list elements
        add_element_label: Label used to customize the add element button.
        remove_element_label: Label used to customize the remove element button.
        no_element_label: Label used in the rule summary if the list is empty.
        editable_order: Can the elements be reordered in the UI
    """

    element_template: FormSpec[ModelT]
    add_element_label: Label = Label("Add new entry")
    remove_element_label: Label = Label("Remove this entry")
    no_element_label: Label = Label("No entries")

    editable_order: bool = True


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceElement:
    """Specifies an element of a multiple choice form

    Args:
        name: Identifier of the MultipleChoiceElement. Must be a valid Python identifier.
        title: Human readable title that will be shown in the UI
    """

    name: str
    title: Title

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"'{self.name}' is not a valid Python identifier")


@dataclass(frozen=True, kw_only=True)
class MultipleChoice(FormSpec[Sequence[str]]):
    """Specifies a multiple choice form

    Args:
        elements: Elements to choose from
        show_toggle_all: Show toggle all elements option in the UI
        prefill: Element names to select by default

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

    prefill: DefaultValue[Sequence[str]] = DefaultValue(())

    def __post_init__(self) -> None:
        available_names = {elem.name for elem in self.elements}
        if invalid := set(self.prefill.value) - available_names:
            raise ValueError(f"Invalid prefill element(s): {', '.join(invalid)}")
