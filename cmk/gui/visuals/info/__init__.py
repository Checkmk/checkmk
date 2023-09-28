#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._base import VisualInfo
from ._infos import register
from ._registry import visual_info_registry, VisualInfoRegistry

__all__ = [
    "VisualInfo",
    "VisualInfoRegistry",
    "visual_info_registry",
    "register",
]
