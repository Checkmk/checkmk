#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.views.row_post_processing import row_post_processor_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_post_processor_registrations() -> None:
    names = [f.__name__ for f in row_post_processor_registry.values()]
    expected = [
        "inventory_row_post_processor",
        "join_service_row_post_processor",
    ]
    assert sorted(names) == sorted(expected)
