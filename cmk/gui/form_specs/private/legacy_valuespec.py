#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any

import cmk.rulesets.v1
import cmk.rulesets.v1.form_specs
from cmk.gui.valuespec import ValueSpec


@dataclass(frozen=True, kw_only=True)
class LegacyValueSpec(cmk.rulesets.v1.form_specs.FormSpec[Any]):
    valuespec: ValueSpec[Any]

    @classmethod
    def wrap(cls, valuespec: ValueSpec[Any]) -> "LegacyValueSpec":
        return cls(
            title=cmk.rulesets.v1.Title(str(valuespec.title() or "")),
            help_text=cmk.rulesets.v1.Help(str(valuespec.help() or "")),
            valuespec=valuespec,
        )
