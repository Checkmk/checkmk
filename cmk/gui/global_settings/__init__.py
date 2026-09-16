#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.global_settings.pages import register
from cmk.gui.global_settings.search import MatchItemGeneratorSettings
from cmk.gui.global_settings.utils import (
    central_settings,
    ensure_page_access,
    render_settings_page,
)

__all__ = [
    "central_settings",
    "ensure_page_access",
    "MatchItemGeneratorSettings",
    "register",
    "render_settings_page",
]
