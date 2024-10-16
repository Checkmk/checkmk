#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from cmk.rulesets.v1.form_specs import FormSpec


@dataclass(frozen=True, kw_only=True)
class Tuple(FormSpec[tuple[object, ...]]):
    elements: Sequence[FormSpec[Any]]
    layout: Literal["vertical", "horizontal", "horizontal_titles_top", "float"] = "vertical"
    show_titles: bool = True
