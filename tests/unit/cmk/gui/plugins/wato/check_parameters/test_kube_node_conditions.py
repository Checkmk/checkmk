#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.check_parameters.kube_node_conditions import migrate


def test_migration_all() -> None:
    old = {
        "ready": 1,
        "memorypressure": 1,
        "diskpressure": 1,
        "pidpressure": 1,
        "networkunavailable": 1,
    }
    new = migrate(old)
    assert new == {
        "conditions": [
            ("Ready", 0, 1, 2),
            ("MemoryPressure", 1, 0, 2),
            ("DiskPressure", 1, 0, 2),
            ("PIDPressure", 1, 0, 2),
            ("NetworkUnavailable", 1, 0, 2),
        ]
    }


def test_migration_empty() -> None:
    new = migrate({})
    assert new == {"conditions": [("Ready", 0, 2, 2)]}


def test_migration_single() -> None:
    new = migrate({"pidpressure": 0})
    assert new == {"conditions": [("PIDPressure", 0, 0, 2), ("Ready", 0, 2, 2)]}
