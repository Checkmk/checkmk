#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec
from cmk.shared_typing.vue_formspec_components import ListOfStringsLayout


@dataclass(frozen=True, kw_only=True)
class ListOfStrings(FormSpec[Sequence[str]]):
    string_spec: FormSpec[str]
    layout: ListOfStringsLayout = ListOfStringsLayout.horizontal
    prefill: DefaultValue[Sequence[str]] = DefaultValue([])
