#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ._config import (
    add_check_plugin,
    get_check_plugin,
    is_registered_check_plugin,
    iter_all_check_plugins,
)

__all__ = [
    "add_check_plugin",
    "get_check_plugin",
    "is_registered_check_plugin",
    "iter_all_check_plugins",
]
