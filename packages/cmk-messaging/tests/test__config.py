#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests"""

from cmk.messaging import get_local_port


# dummy test during package creation. Feel free to remove.
def test_get_local_port() -> None:
    assert callable(get_local_port)
