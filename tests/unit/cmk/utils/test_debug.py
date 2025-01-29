#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.debug


def test_toggle() -> None:
    cmk.ccc.debug.enable()

    assert cmk.ccc.debug.enabled() is True

    cmk.ccc.debug.disable()

    assert cmk.ccc.debug.enabled() is False
