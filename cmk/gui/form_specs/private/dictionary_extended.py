#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from cmk.gui.form_specs.vue.shared_type_defs import DictionaryLayout

from cmk.rulesets.v1 import Message
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, FormSpec

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class DictionaryExtended(FormSpec[Mapping[str, object]]):
    """
    Specifies a (multi-)selection of configuration options.

    Consumer model:
    ***************
    **Type**: ``dict[str, object]``
    The configured value will be presented as a dictionary consisting of the names of provided
    configuration options and their respective consumer models.

    Arguments:
    **********
    """

    elements: Mapping[str, DictElement[Any]]
    """key-value mapping where the key identifies the option and the value specifies how
    the nested form can be configured. The key has to be a valid Python identifier."""

    no_elements_text: Message = Message("(no parameters)")
    """Text to show if no elements are specified"""

    ignored_elements: tuple[str, ...] = ()
    """Elements that can no longer be configured, but aren't removed from rules if they are present.
    They might be ignored when rendering the ruleset.
    You can use these to deprecate elements, to avoid breaking the old configurations.
    """

    prefill: DefaultValue[Mapping[str, object]] | None = None
    layout: DictionaryLayout = DictionaryLayout.one_column
