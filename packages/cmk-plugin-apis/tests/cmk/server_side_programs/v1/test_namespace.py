#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
+----------------------------------------------------------+
|              Achtung Alles Lookenskeepers!               |
|              =============================               |
|                                                          |
| The extend of this API is well documented, and the       |
| result of careful negotiation.                           |
| Once promoted to a stable version it must not be changed.|
+----------------------------------------------------------+
"""

from cmk.server_side_programs import v1_unstable as api


def test_api_names() -> None:
    assert set(api.__all__) == {
        "vcrtrace",
        "HostnameValidationAdapter",
        "Storage",
    }
