#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import TypeVar

from cmk.rulesets.v1.form_specs import DictGroup, Dictionary
from cmk.shared_typing.vue_formspec_components import DictionaryGroupLayout

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class DictionaryExtended(Dictionary):
    # Usage of default_checked is advised against: if you want an optional
    # element prefilled with options, reconsider and flip your approach. If
    # something should be the default, it should not need configuration. Add
    # complexity (stray from the default) by checking boxes, not unchecking
    # them. Another approach would be to use a cascading single choice with your
    # default preselected.
    default_checked: list[str] | None = None

    def __post_init__(self) -> None:
        for checked in self.default_checked or []:
            if checked not in self.elements:
                raise ValueError(f"Default checked element '{checked}' is not in elements")


@dataclass(frozen=True, kw_only=True)
class DictGroupExtended(DictGroup):
    """Specification for a group of dictionary elements that are more closely related thematically
    than the other elements. A group is identified by its title and help text.
    """

    layout: DictionaryGroupLayout = DictionaryGroupLayout.horizontal
