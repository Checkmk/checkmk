#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.unstable import SingleChoiceEditable
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.form_specs.unstable.passwordstore_password import PasswordStorePassword
from cmk.rulesets.v1.form_specs import (
    FormSpec,
)
from cmk.shared_typing.configuration_entity import ConfigEntityType


def _password_disk_to_ui(value: object) -> str:
    match value:
        case ("cmk_postprocessed", "stored_password", (str(pw_id), "")):
            return pw_id
        case _:
            raise MKGeneralException("Could read stored password configuration")


def _password_ui_to_disk(value: object) -> tuple[str, str, tuple[str, str]]:
    match value:
        case str(pw_id):
            return "cmk_postprocessed", "stored_password", (pw_id, "")
        case _:
            raise MKGeneralException("Could not store password configuration")


def recompose(form_spec: FormSpec[Any]) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if not isinstance(form_spec, PasswordStorePassword):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a PasswordStorePassword form spec, got {type(form_spec)}"
        )

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=SingleChoiceEditable(
            title=form_spec.title,
            help_text=form_spec.help_text,
            entity_type=ConfigEntityType.passwordstore_password,
            entity_type_specifier="all",
            allow_editing_existing_elements=False,
        ),
        from_disk=_password_disk_to_ui,
        to_disk=_password_ui_to_disk,
        custom_validate=form_spec.custom_validate,  # type: ignore[arg-type]
        migrate=form_spec.migrate,
    )
