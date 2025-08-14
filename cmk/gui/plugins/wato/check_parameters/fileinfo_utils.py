#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DictElement, TimeMagnitude, TimeSpan


def get_fileinfo_negative_age_tolerance_element() -> DictElement[float]:
    """Returns a DictElement for the negative age tolerance setting in fileinfo rules."""
    return DictElement(
        required=False,
        parameter_form=TimeSpan(
            displayed_magnitudes=[
                TimeMagnitude.DAY,
                TimeMagnitude.HOUR,
                TimeMagnitude.MINUTE,
                TimeMagnitude.SECOND,
            ],
            migrate=float,  # type: ignore[arg-type] # wrong type, right behaviour
            title=Title("Negative age tolerance"),
            help_text=Help(
                "The file age of files with creation time from the future will be set to 0 if "
                "the creation time is within the tolerance period."
            ),
        ),
    )
