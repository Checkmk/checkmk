#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, CascadingDropdown, Tuple


def wrap_with_no_levels_dropdown(title, value_spec) -> CascadingDropdown:
    return CascadingDropdown(
        title=title,
        choices=[
            ("no_levels", _("No Levels")),
            ("levels", _("Impose levels"), value_spec),
        ],
        default_value="no_levels",
    )


def age_levels_dropdown(
    title: str, default_choice: Literal["levels", "no_levels"] = "no_levels"
) -> CascadingDropdown:
    return CascadingDropdown(
        title=title,
        choices=[
            (
                "no_levels",
                _("No levels"),
                None,
            ),
            (
                "levels",
                _("Impose levels"),
                Tuple(
                    elements=[
                        Age(title=_("Warning after"), default_value=300),
                        Age(title=_("Critical after"), default_value=600),
                    ],
                ),
            ),
        ],
        default_value=default_choice,
    )
