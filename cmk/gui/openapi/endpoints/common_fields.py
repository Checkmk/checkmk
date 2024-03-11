#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import fields as gui_fields

EXISTING_FOLDER_PATTERN = r"^(?:(?:[~\\\/]|(?:[~\\\/][-\w]+)+[~\\\/]?)|[0-9a-fA-F]{32})$"

EXISTING_FOLDER = gui_fields.FolderField(
    example="/",
    required=True,
    pattern=EXISTING_FOLDER_PATTERN,
)
