#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping

from cmk.gui import fields as gui_fields

from cmk.fields import Boolean

EXISTING_FOLDER_PATTERN = r"^(?:(?:[~\\\/]|(?:[~\\\/][-\w]+)+[~\\\/]?)|[0-9a-fA-F]{32})$"

EXISTING_FOLDER = gui_fields.FolderField(
    example="/",
    required=True,
    pattern=EXISTING_FOLDER_PATTERN,
)


def field_include_links(description: str | None = None) -> Mapping[str, Boolean]:
    return {
        "include_links": Boolean(
            load_default=False,
            required=False,
            example=False,
            description=description
            or "Flag which toggles whether the links field of the individual values should be populated.",
        )
    }


def field_include_extensions(description: str | None = None) -> Mapping[str, Boolean]:
    return {
        "include_extensions": Boolean(
            load_default=True,
            required=False,
            example=True,
            description=description
            or "Flag which toggles whether the extensions field of the individual values should be populated.",
        )
    }
