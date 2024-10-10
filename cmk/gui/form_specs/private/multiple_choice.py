#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import Enum

from cmk.rulesets.v1.form_specs._composed import MultipleChoice


@dataclass(frozen=True, kw_only=True)
class AdaptiveMultipleChoiceLayout(str, Enum):
    auto = "auto"
    dual_list = "dual_list"
    checkbox_list = "checkbox_list"


@dataclass(frozen=True, kw_only=True)
class AdaptiveMultipleChoice(MultipleChoice):
    layout: AdaptiveMultipleChoiceLayout = AdaptiveMultipleChoiceLayout.auto
