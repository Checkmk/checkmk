#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

from cmk.rulesets.v1.form_specs import DefaultValue, DictGroup, Dictionary
from cmk.shared_typing.vue_formspec_components import DictionaryGroupLayout, DictionaryLayout

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class DictionaryExtended(Dictionary):
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

    prefill: DefaultValue[Mapping[str, object]] | None = None
    layout: DictionaryLayout = DictionaryLayout.one_column

    def __post_init__(self) -> None:
        pass


@dataclass(frozen=True, kw_only=True)
class DictGroupExtended(DictGroup):
    """Specification for a group of dictionary elements that are more closely related thematically
    than the other elements. A group is identified by its title and help text.
    """

    layout: DictionaryGroupLayout = DictionaryGroupLayout.horizontal
