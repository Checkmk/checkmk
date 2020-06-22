#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager

import cmk.utils.debug


@contextmanager
def cmk_debug_enabled():
    debug_mode = cmk.utils.debug.enabled()
    cmk.utils.debug.enable()
    try:
        yield
    finally:
        if debug_mode:
            cmk.utils.debug.enable()
        else:
            cmk.utils.debug.disable()
