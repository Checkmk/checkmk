#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, CascadingDropdown, Tuple, ValueSpec


def wrap_with_no_levels_dropdown(
    title: str | None,
    value_spec: ValueSpec,
    default_choice: Literal["levels", "no_levels"] = "no_levels",
) -> CascadingDropdown:
    return CascadingDropdown(
        title=title,
        choices=[
            ("no_levels", _("Do not impose levels")),
            ("levels", _("Impose levels"), value_spec),
        ],
        default_value=default_choice,
    )


def age_levels_dropdown(
    title: str | None = None, default_choice: Literal["levels", "no_levels"] = "no_levels"
) -> CascadingDropdown:
    return wrap_with_no_levels_dropdown(
        title=title,
        value_spec=Tuple(
            elements=[
                Age(title=_("Warning after"), default_value=300),
                Age(title=_("Critical after"), default_value=600),
            ],
        ),
        default_choice=default_choice,
    )
