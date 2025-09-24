#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.gui.form_specs.unstable.legacy_converter import (
    Tuple,
)
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import FormSpec


def TupleLevels(
    elements: list[FormSpec[Any]], title: Title | None = None, help_text: Help | None = None
) -> Tuple:
    # This function acts as placeholder and indicates that the TupleLevels
    # should be converted to a SimpleLevels form spec.
    return Tuple(title=title, help_text=help_text, elements=elements)
