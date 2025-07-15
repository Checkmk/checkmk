#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from cmk.gui.form_specs.private.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.form_specs.private.single_choice_extended import SingleChoiceElementExtended
from cmk.gui.form_specs.private.validators import ModelT

from cmk.rulesets.v1 import Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DefaultValue,
    FormSpec,
    InputHint,
    SingleChoice,
)
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout


@dataclass(frozen=True, kw_only=True)
class UniqueSingleChoiceElement:
    unique: bool = True
    parameter_form: SingleChoiceElementExtended[Any]


@dataclass(frozen=True, kw_only=True)
class UniqueCascadingSingleChoiceElement:
    unique: bool = True
    parameter_form: CascadingSingleChoiceElementExtended[Any]


@dataclass(frozen=True, kw_only=True)
class ListUniqueSelection(FormSpec[Sequence[ModelT]]):
    """
    Specifies a list of single choice configuration elements of the same type.
    The elements in the list can be configured to be unique.

    Consumer model:
    ***************
    **Type**: ``list[object]``
    The configured value will be presented as a list consisting of the consumer models of the
    configured elements.

    Arguments:
    **********
    """

    elements: Sequence[UniqueSingleChoiceElement] | Sequence[UniqueCascadingSingleChoiceElement]
    """Configuration specification of the list elements."""
    no_elements_text: Message | None = None
    """Text to show if no elements are given."""
    single_choice_label: Label | None = None
    """Text displayed in front of the input field."""
    single_choice_prefill: DefaultValue[Any] | InputHint[Title] = InputHint(Title("Please choose"))
    """Name of pre-selected choice. If DefaultValue is used, it must be one of the elements names.
    If InputHint is used, its title will be shown as a placeholder in the UI, requiring the user to
    select a value."""
    single_choice_type: type[SingleChoice] | type[CascadingSingleChoice] = SingleChoice
    """Type of the single choice elements."""
    cascading_single_choice_layout: CascadingSingleChoiceLayout = (
        CascadingSingleChoiceLayout.vertical
    )
    """Layout of the cascading single choice, only applies if CascadingSingleChoice is selected."""

    add_element_label: Label = Label("Add new entry")
    """Label used to customize the add element button."""
    remove_element_label: Label = Label("Remove this entry")
    """Label used to customize the remove element button."""
    no_element_label: Label = Label("No entries")
    """Label used in the rule summary if the list is empty."""
    prefill: DefaultValue[Sequence[ModelT]] = DefaultValue([])

    def __post_init__(self):
        if self.single_choice_type is SingleChoice:
            if not all(isinstance(element, UniqueSingleChoiceElement) for element in self.elements):
                raise ValueError(
                    "All elements must be of type UniqueSingleChoiceElement when using SingleChoice."
                )
        if self.single_choice_type is CascadingSingleChoice:
            if not all(
                isinstance(element, UniqueCascadingSingleChoiceElement) for element in self.elements
            ):
                raise ValueError(
                    "All elements must be of type UniqueCascadingSingleChoiceElement when using CascadingSingleChoice."
                )
