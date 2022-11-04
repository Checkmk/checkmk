#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple

from cmk.utils.translations import TranslationOptions
from cmk.utils.type_defs import SectionName


class AgentParserConfig(NamedTuple):
    # Ordered alphabetically:  Do not rely on the order of the fields.
    check_interval: int
    encoding_fallback: str
    keep_outdated: bool
    translation: TranslationOptions
    agent_simulator: bool


class SNMPParserConfig(NamedTuple):
    # Ordered alphabetically:  Do not rely on the order of the fields.
    check_intervals: Mapping[SectionName, int | None]
    keep_outdated: bool
