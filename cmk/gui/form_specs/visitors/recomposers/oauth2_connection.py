#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.unstable import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.oauth2_connections.watolib.store import load_oauth2_connections
from cmk.rulesets.internal.form_specs import OAuth2Connection
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    FormSpec,
)


def _oauth2_connection_disk_to_ui(value: object) -> str:
    match value:
        case ("cmk_postprocessed", "oauth2_connection", str(connection_id)):
            return connection_id
        case _:
            raise MKGeneralException("Could not read OAuth2 connection configuration")


def _oauth2_connection_ui_to_disk(value: object) -> tuple[str, str, str]:
    match value:
        case str(connection_id):
            return "cmk_postprocessed", "oauth2_connection", connection_id
        case _:
            raise MKGeneralException("Could not store OAuth2 connection configuration")


def recompose(
    form_spec: FormSpec[Any],
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if not isinstance(form_spec, OAuth2Connection):
        raise MKGeneralException(
            f"Cannot recompose FormSpec. Expected an OAuth2Connection FormSpec, got {type(form_spec)}"
        )

    oauth2_connections = load_oauth2_connections()
    oauth2_connection_choices: list[SingleChoiceElementExtended[str]] = [
        SingleChoiceElementExtended[str](
            name=ident,
            title=Title("%s") % connection["title"],
        )
        for ident, connection in oauth2_connections.items()
    ]

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=SingleChoiceExtended[str](
            title=form_spec.title or Title("OAuth2 connection"),
            help_text=form_spec.help_text,
            elements=oauth2_connection_choices,
        ),
        from_disk=_oauth2_connection_disk_to_ui,
        to_disk=_oauth2_connection_ui_to_disk,
        custom_validate=form_spec.custom_validate,  # type: ignore[arg-type]
        migrate=form_spec.migrate,
    )
