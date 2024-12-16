#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.watolib.timeperiods import load_timeperiods

from cmk.rulesets.v1 import Help, Title


def _get_timeperiod_choices() -> Sequence[SingleChoiceElementExtended[str]]:
    timeperiods = load_timeperiods()

    elements = [
        SingleChoiceElementExtended(
            name=name,
            title=Title(  # pylint: disable=localization-of-non-literal-string
                "{} - {}".format(name, tp["alias"])
            ),
        )
        for (name, tp) in timeperiods.items()
    ]
    if "24X7" not in list(timeperiods.keys()):
        always = SingleChoiceElementExtended(name="24X7", title=Title("Always"))
        elements.insert(0, always)

    return sorted(elements, key=lambda x: x.title.localize(translate_to_current_language).lower())


def create_timeperiod_selection(
    title: Title | None = None,
    help_text: Help | None = None,
) -> SingleChoiceExtended[str]:
    return SingleChoiceExtended[str](
        title=title or Title("Select a time period"),
        help_text=help_text,
        elements=_get_timeperiod_choices(),
    )
