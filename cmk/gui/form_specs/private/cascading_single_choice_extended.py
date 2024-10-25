#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from cmk.gui.form_specs.vue.shared_type_defs import CascadingSingleChoiceLayout

from cmk.rulesets.v1.form_specs import CascadingSingleChoice


@dataclass(frozen=True, kw_only=True)
class CascadingSingleChoiceExtended(CascadingSingleChoice):
    layout: CascadingSingleChoiceLayout = CascadingSingleChoiceLayout.vertical
