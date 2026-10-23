#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec, InputHint
from cmk.shared_typing.configuration_entity import ConfigEntityType


@dataclass(frozen=True, kw_only=True)
class SingleChoiceEditable(FormSpec[str]):
    entity_type: ConfigEntityType
    entity_type_specifier: str
    prefill: DefaultValue[str] | InputHint[Title] = InputHint(Title("Please select an element"))
    create_element_label: Label = Label("Create")
    allow_editing_existing_elements: bool = True


@dataclass(frozen=True, kw_only=True)
class FolderChoiceEditable(SingleChoiceEditable):
    """A choice of a folder with a button to create a new one

    `folder_choices` returns the path and the full title of each folder the user may choose.
    """

    entity_type: ConfigEntityType = ConfigEntityType.folder
    entity_type_specifier: str = "all"  # must not be empty, unused
    folder_choices: Callable[[], Sequence[tuple[str, str]]]
