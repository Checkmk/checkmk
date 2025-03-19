#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.generators.folder import create_full_path_folder_choice
from cmk.gui.form_specs.private import Folder, SingleChoiceEditable

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import DefaultValue, FormSpec
from cmk.shared_typing.configuration_entity import ConfigEntityType


def recompose(form_spec: FormSpec[Any]) -> FormSpec[Any]:
    if not isinstance(form_spec, Folder):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a Folder form spec, got {type(form_spec)}"
        )

    if form_spec.allow_new_folder_creation:
        return SingleChoiceEditable(
            # FormSpec
            title=form_spec.title,
            help_text=form_spec.help_text,
            custom_validate=form_spec.custom_validate,
            # SingleChoiceEditable
            entity_type=ConfigEntityType.folder,
            entity_type_specifier="all",  # must not be empty, unused
            prefill=DefaultValue(""),
            create_element_label=Label("Create new"),
            allow_editing_existing_elements=False,
        )

    return create_full_path_folder_choice(form_spec.title or Title("Folder"), form_spec.help_text)
