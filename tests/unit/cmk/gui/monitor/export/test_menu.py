#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.monitor.export import MonitorExportMenu


@pytest.mark.usefixtures("user_without_permissions")
def test_export_dropdown_hidden_without_permission() -> None:
    assert MonitorExportMenu().dropdowns() == []


@pytest.mark.usefixtures("with_user_login")
def test_export_dropdown_offers_csv_and_json_with_permission() -> None:
    assert [
        entry.name
        for dropdown in MonitorExportMenu().dropdowns()
        for topic in dropdown.topics
        for entry in topic.entries
    ] == ["export_csv", "export_json"]
