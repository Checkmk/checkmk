#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.sidebar import snapin_registry


@pytest.mark.parametrize(
    "snapin_name",
    ["admin_mini", "mkeventd_performance", "tactical_overview", "tag_tree"],
)
def test_status_snapin_refreshes_regularly(snapin_name: str) -> None:
    assert snapin_registry[snapin_name].refresh_regularly()
