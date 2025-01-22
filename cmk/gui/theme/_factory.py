#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from flask import current_app

from cmk.ccc.version import edition

from cmk.utils.paths import local_web_dir, omd_root, web_dir

from ._theme_type import Theme


def make_theme() -> Theme:
    return Theme(
        edition=edition(omd_root),
        web_dir=Path(web_dir),
        local_web_dir=local_web_dir,
        validate_choices=current_app.debug,
    )
