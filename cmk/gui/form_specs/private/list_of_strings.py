#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Sequence

from cmk.gui.form_specs.vue.shared_type_defs import ListOfStringsLayout

from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec


@dataclass(frozen=True, kw_only=True)
class ListOfStrings(FormSpec[Sequence[str]]):
    string_spec: FormSpec[str]
    layout: ListOfStringsLayout = ListOfStringsLayout.horizontal
    prefill: DefaultValue[Sequence[str]] = DefaultValue([])
