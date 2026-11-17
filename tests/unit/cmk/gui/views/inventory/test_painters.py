#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.views.inventory._painters import _compute_attribute_painter_data
from cmk.inventory.structured_data import SDKey, SDNodeName


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="crash group 4806")
@pytest.mark.usefixtures("request_context")
def test_attribute_of_a_row_without_host_name() -> None:
    # A view of another data source, e.g. the log, can show a host inventory
    # attribute without fetching the host name; its inventory is then None.
    row = {"site": "heute", "log_lineno": 1, "host_inventory": None}

    assert (
        _compute_attribute_painter_data(
            row, (SDNodeName("hardware"), SDNodeName("system")), SDKey("product")
        )
        is None
    )
