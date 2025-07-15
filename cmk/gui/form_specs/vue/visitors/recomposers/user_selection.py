#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId

from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.private import (
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.private.user_selection import UserSelection
from cmk.gui.userdb._user_selection import generate_wato_users_elements_function

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import FormSpec


def recompose(form_spec: FormSpec[Any]) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if not isinstance(form_spec, UserSelection):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a UserSelection form spec, got {type(form_spec)}"
        )

    legacy_filter = form_spec.filter.to_legacy()

    elements = []

    for user_id, alias in generate_wato_users_elements_function(
        legacy_filter.only_contacts, legacy_filter.only_automation
    )():
        elements.append(SingleChoiceElementExtended(name=user_id, title=Title("%s") % alias))

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=SingleChoiceExtended(
            # FormSpec:
            title=form_spec.title,
            help_text=form_spec.help_text,
            migrate=form_spec.migrate,
            custom_validate=form_spec.custom_validate,
            # SingleChoice
            label=form_spec.label,
            elements=elements,
        ),
        # it's a simple string on disk, but in python we want it to be UserId
        # the form_spec world will see the UserId, but
        # the check world will still only see what's saved on disk: a string.
        from_disk=_from_disk,
        to_disk=_to_disk,
    )


def _from_disk(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"UserSelection from disk transform expected str, got '{value}'")
    return UserId(value)


def _to_disk(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, UserId):
        raise ValueError(f"UserSelection to disk transform expected UserId, got '{value}'")
    return str(value)
