#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.diagnostics.engine import DumpSelection


def test_dump_selection_round_trip() -> None:
    selection = DumpSelection(plugins=["general_info", "hw_info"], checkmk_server_host="srv")
    assert DumpSelection.deserialize(selection.serialize()) == selection


def test_dump_selection_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        DumpSelection.deserialize("not json")
    with pytest.raises(ValueError):
        DumpSelection.deserialize('{"v": 2, "plugins": []}')
