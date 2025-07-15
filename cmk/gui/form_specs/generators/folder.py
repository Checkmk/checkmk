#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence

from cmk.gui.form_specs.private import (
    SingleChoiceEditable,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue
from cmk.shared_typing.configuration_entity import ConfigEntityType


def create_full_path_folder_choice(
    title: Title,
    help_text: Help | None,
    custom_validate: Sequence[Callable[[str], object]] | None = None,
    allow_new_folder_creation: bool = False,
) -> SingleChoiceExtended[str] | SingleChoiceEditable:
    choices = folder_tree().folder_choices_fulltitle()

    if allow_new_folder_creation:
        return SingleChoiceEditable(
            # FormSpec
            title=title,
            help_text=help_text,
            custom_validate=custom_validate,
            # SingleChoiceEditable
            entity_type=ConfigEntityType.folder,
            entity_type_specifier="all",  # must not be empty, unused
            prefill=DefaultValue(""),
            create_element_label=Label("Create new"),
            allow_editing_existing_elements=False,
        )

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
        custom_validate=custom_validate,
    )
