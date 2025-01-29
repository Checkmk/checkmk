#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeAlias

from cmk.rulesets.v1 import Label
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.vue_formspec_components import ConditionGroup

ConditionID: TypeAlias = str
ConditionGroupID: TypeAlias = str
_IsCondition: TypeAlias = ConditionID
_IsNotCondition: TypeAlias = dict[Literal["$ne"], ConditionID]
_OrCondition: TypeAlias = dict[Literal["$or"], list[ConditionID]]
_NorCondition: TypeAlias = dict[Literal["$nor"], list[ConditionID]]
Condition: TypeAlias = _OrCondition | _NorCondition | _IsNotCondition | _IsCondition
Conditions: TypeAlias = dict[ConditionGroupID, Condition]


@dataclass(frozen=True, kw_only=True)
class ConditionChoices(FormSpec[Conditions]):
    add_condition_group_label: Label
    select_condition_group_to_add: Label
    no_more_condition_groups_to_add: Label
    get_conditions: Callable[[], dict[str, ConditionGroup]]
