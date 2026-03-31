#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.rulesets.v1 import Label
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing.vue_formspec_components import Condition as Condition
from cmk.shared_typing.vue_formspec_components import ConditionGroup as ConditionGroup

type ConditionID = str
type ConditionGroupID = str
type _IsCondition = ConditionID
type _IsNotCondition = Mapping[Literal["$ne"], ConditionID]
type _OrCondition = Mapping[Literal["$or"], Sequence[ConditionID]]
type _NorCondition = Mapping[Literal["$nor"], Sequence[ConditionID]]
type ConditionTypeDisk = _OrCondition | _NorCondition | _IsNotCondition | _IsCondition
type ConditionsTypeDisk = Mapping[ConditionGroupID, ConditionTypeDisk]


@dataclass(frozen=True, kw_only=True)
class ConditionChoices(FormSpec[ConditionsTypeDisk]):
    add_condition_group_label: Label
    select_condition_group_to_add: Label
    no_more_condition_groups_to_add: Label
    get_conditions: Callable[[], Mapping[str, ConditionGroup]]
