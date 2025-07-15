#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any

from cmk.gui.valuespec import ValueSpec

import cmk.rulesets.v1
import cmk.rulesets.v1.form_specs


@dataclass(frozen=True, kw_only=True)
class LegacyValueSpec(cmk.rulesets.v1.form_specs.FormSpec[Any]):
    valuespec: ValueSpec[Any]

    @classmethod
    def wrap(cls, valuespec: ValueSpec[Any]) -> "LegacyValueSpec":
        return cls(
            title=cmk.rulesets.v1.Title(  # pylint: disable=localization-of-non-literal-string
                str(valuespec.title() or "")
            ),  # pylint: disable=localization-of-non-literal-string
            help_text=cmk.rulesets.v1.Help(  # pylint: disable=localization-of-non-literal-string
                str(valuespec.help() or "")
            ),
            valuespec=valuespec,
        )
