#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec, MultipleChoiceElement
from cmk.shared_typing.vue_formspec_components import Autocompleter


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceExtendedLayout(str, Enum):
    auto = "auto"
    dual_list = "dual_list"
    checkbox_list = "checkbox_list"


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceElementExtended(MultipleChoiceElement):
    """Specifies an element of a multiple choice form.

    It can and should only be used internally when using it to generate MultipleChoiceExtended
    FormSpecs when the input data is not predefined, for example when creating FormSpecs based on
    user input, like for contact groups.
    """

    def __post_init__(self):
        pass


@dataclass(frozen=True, kw_only=True)
class MultipleChoiceExtended(FormSpec[Sequence[str]]):
    elements: Sequence[MultipleChoiceElement] | Autocompleter
    show_toggle_all: bool = False
    prefill: DefaultValue[Sequence[str]] = DefaultValue(())
    layout: MultipleChoiceExtendedLayout = MultipleChoiceExtendedLayout.auto

    def __post_init__(self) -> None:
        if not isinstance(self.elements, Autocompleter):
            available_names = {elem.name for elem in self.elements}
            if invalid := set(self.prefill.value) - available_names:
                raise ValueError(f"Invalid prefill element(s): {', '.join(invalid)}")
