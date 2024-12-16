#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Generic

from cmk.rulesets.v1.form_specs import CascadingSingleChoice, CascadingSingleChoiceElement
from cmk.rulesets.v1.form_specs._base import ModelT
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceElementExtended(CascadingSingleChoiceElement[ModelT], Generic[ModelT]):
    """Specifies an element of a single choice cascading form.

    It can and should only be used internally when using it to generate CascadingSingleChoiceExtended
    FormSpecs when the input data is not predefined, for example when creating FormSpecs based on
    user input, like for contact groups.
    """

    def __post_init__(self):
        pass


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceExtended(CascadingSingleChoice):
    layout: CascadingSingleChoiceLayout = CascadingSingleChoiceLayout.vertical
