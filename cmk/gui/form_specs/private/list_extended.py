#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar

from cmk.gui.form_specs.private.validators import ModelT

from cmk.rulesets.v1 import Label
from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class ListExtended(FormSpec[Sequence[ModelT]]):
    """
    Specifies a list of configuration elements of the same type.

    Consumer model:
    ***************
    **Type**: ``list[object]``
    The configured value will be presented as a list consisting of the consumer models of the
    configured elements.

    Arguments:
    **********
    """

    element_template: FormSpec[ModelT]
    """Configuration specification of the list elements."""
    add_element_label: Label = Label("Add new entry")
    """Label used to customize the add element button."""
    remove_element_label: Label = Label("Remove this entry")
    """Label used to customize the remove element button."""
    no_element_label: Label = Label("No entries")
    """Label used in the rule summary if the list is empty."""

    editable_order: bool = True
    """Indicate if the users should be able to reorder the elements in the UI."""

    prefill: DefaultValue[Sequence[ModelT]]
