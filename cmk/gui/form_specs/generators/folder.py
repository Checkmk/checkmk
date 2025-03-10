#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue


def create_full_path_folder_choice(title: Title, help_text: Help) -> SingleChoiceExtended[str]:
    choices = folder_tree().folder_choices_fulltitle()
    return SingleChoiceExtended[str](
        title=title,
        help_text=help_text,
        elements=[
            SingleChoiceElementExtended(
                name=choice[0],
                title=Title(choice[1]),  # pylint: disable=localization-of-non-literal-string
            )
            for choice in choices
        ],
        prefill=DefaultValue(""),
    )
