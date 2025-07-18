#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.wato.filters import FilterWatoFolder


# mock_livestatus does not support Stats queries at the moment. We need to mock the function away
# for the "wato_folder" filter test to pass.
@pytest.fixture(name="mock_wato_folders")
def fixture_mock_wato_folders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FilterWatoFolder, "_fetch_folders", lambda s: {""})
