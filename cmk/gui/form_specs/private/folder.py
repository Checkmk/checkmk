#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.rulesets.v1 import form_specs


@dataclass(frozen=True, kw_only=True)
class Folder(form_specs.FormSpec[str]):
    """A prefix of "Main/" is always rendered in front of the input field to indicate that the
    folder will be located under the root folder.
    Set an input_hint to suggest a specific folder under the root one. The input_hint will be
    rendered within the input field.
    """

    input_hint: str | None = None
