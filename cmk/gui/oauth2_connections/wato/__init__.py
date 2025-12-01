#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from ._main_module import register as register_main_module
from ._modes import register as register_modes
from ._pages import register as register_pages

__all__ = [
    "register_modes",
    "register_pages",
    "register_main_module",
]
