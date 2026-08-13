#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Port of the LogLevelChoice() valuespec."""

import logging

import cmk.utils.log
from cmk.rulesets.internal.form_specs import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue


def LogLevelChoice(
    *,
    title: Title | None = None,
    help_text: Help | None = None,
    with_verbose: bool = True,
    prefill: DefaultValue[int] | None = None,
) -> SingleChoiceExtended[int]:
    elements = [
        SingleChoiceElementExtended(name=logging.CRITICAL, title=Title("Critical")),
        SingleChoiceElementExtended(name=logging.ERROR, title=Title("Error")),
        SingleChoiceElementExtended(name=logging.WARNING, title=Title("Warning")),
        SingleChoiceElementExtended(name=logging.INFO, title=Title("Informational")),
        *(
            [SingleChoiceElementExtended(name=cmk.utils.log.VERBOSE, title=Title("Verbose"))]
            if with_verbose
            else []
        ),
        SingleChoiceElementExtended(name=logging.DEBUG, title=Title("Debug")),
    ]
    return SingleChoiceExtended[int](
        title=title,
        help_text=help_text,
        elements=elements,
        prefill=prefill if prefill is not None else DefaultValue(logging.WARNING),
    )
