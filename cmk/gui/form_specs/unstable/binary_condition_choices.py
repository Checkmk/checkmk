#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass

from cmk.rulesets.v1 import Label
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.vue_formspec_components import BinaryCondition as BinaryCondition
from cmk.shared_typing.vue_formspec_components import (
    BinaryConditionChoicesValue as BinaryConditionChoicesValue,
)


@dataclass(frozen=True, kw_only=True)
class BinaryConditionChoices(FormSpec[BinaryConditionChoicesValue]):
    label: Label
    get_conditions: Callable[[], list[BinaryCondition]]
