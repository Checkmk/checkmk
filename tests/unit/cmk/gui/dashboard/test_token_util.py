#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for token_util helpers."""

import pytest

from cmk.gui.dashboard.token_util import get_dashboard_widget_by_id, InvalidWidgetError


def test_idor_protection_widget_not_in_dashboard() -> None:
    """widget_id not in dashboard must raise InvalidWidgetError."""
    # Simulate a dashboard with one widget
    fake_dashboard = {
        "name": "test_dashboard",
        "owner": "cmkadmin",
        "dashlets": [
            {"type": "pnpgraph", "context": {}},
        ],
    }
    with pytest.raises(InvalidWidgetError):
        get_dashboard_widget_by_id(fake_dashboard, "other_dashboard-0")  # type: ignore[arg-type]

    with pytest.raises(InvalidWidgetError):
        get_dashboard_widget_by_id(fake_dashboard, "test_dashboard-1")  # type: ignore[arg-type]

    # The valid one should work
    config = get_dashboard_widget_by_id(fake_dashboard, "test_dashboard-0")  # type: ignore[arg-type]
    assert config["type"] == "pnpgraph"
