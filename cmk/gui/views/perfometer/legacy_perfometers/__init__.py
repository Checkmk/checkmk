#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from . import active_checks, check_mk
from .utils import perfometers, render_metricometer


def register() -> None:
    active_checks.register()
    check_mk.register()


__all__ = [
    "register",
    "perfometers",
    "render_metricometer",
]
