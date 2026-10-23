#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.pagetypes import builtin_pagetype_topic_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_pagetype_topics() -> None:
    assert sorted(builtin_pagetype_topic_registry) == [
        "analyze",
        "applications",
        "bi",
        "cloud",
        "events",
        "history",
        "inventory",
        "it_efficiency",
        "monitoring",
        "my_workplace",
        "other",
        "overview",
        "problems",
        "synthetic_monitoring",
    ]
