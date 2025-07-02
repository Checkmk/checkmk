#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.rulesets.v1 import Label
from cmk.rulesets.v1.form_specs import FieldSize, FormSpec, InputHint, Prefill
from cmk.shared_typing.vue_formspec_components import Autocompleter as Autocompleter
from cmk.shared_typing.vue_formspec_components import AutocompleterData as AutocompleterData
from cmk.shared_typing.vue_formspec_components import AutocompleterParams as AutocompleterParams


@dataclass(frozen=True, kw_only=True)
class StringAutocompleter(FormSpec[str]):
    label: Label | None = None
    macro_support: bool = False
    prefill: Prefill[str] = InputHint("")
    field_size: FieldSize = FieldSize.MEDIUM
    autocompleter: Autocompleter | None = None
