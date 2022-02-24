#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.debug


def test_toggle():
    cmk.utils.debug.enable()

    assert cmk.utils.debug.enabled() is True
    assert cmk.utils.debug.disabled() is False

    cmk.utils.debug.disable()

    assert cmk.utils.debug.enabled() is False
    assert cmk.utils.debug.disabled() is True
