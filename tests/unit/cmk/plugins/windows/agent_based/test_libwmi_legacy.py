#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.windows.agent_based.libwmi_legacy import get_levels_quadruple


def test_get_levels_quadruple_with_levels_stored_as_list() -> None:
    # Levels reach the check as lists rather than tuples depending on how the
    # rule was written; only "upper" is configured here, as in the crash report.
    assert get_levels_quadruple({"upper": [10.0, 15.0]}) == (10.0, 15.0, None, None)
