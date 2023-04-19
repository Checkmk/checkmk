#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.valuespec import Age


def get_fileinfo_negative_age_tolerance_element() -> tuple[str, Age]:
    return (
        "negative_age_tolerance",
        Age(
            title="Negative age tolerance",
            help="The file age of files with creation time from the future"
            " will be set to 0 if the creation time is within the tolerance period.",
        ),
    )
