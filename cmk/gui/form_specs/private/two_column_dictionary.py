#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.rulesets.v1.form_specs import Dictionary


@dataclass(frozen=True, kw_only=True)
class TwoColumnDictionary(Dictionary):
    # Don't use default_checked, it's toxic: if you want an optional element prefilled with options,
    # reconsider and flip your approach. If something should be the default, it should not need
    # configuration. Add complexity (stray from the default) by checking boxes, not unchecking them.
    default_checked: list[str] | None = None

    def __post_init__(self) -> None:
        for checked in self.default_checked or []:
            if checked not in self.elements:
                raise ValueError(f"Default checked element '{checked}' is not in elements")
