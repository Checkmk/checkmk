#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.docker.rulesets.mk_docker import migrate


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, {"deployment": ("do_not_deploy", None)}),
        (
            {"node": [], "containers": [], "container_id": "short"},
            {
                "deployment": ("sync", None),
                "node": [],
                "containers": [],
                "container_id": "short",
            },
        ),
        (
            {
                "node": [],
                "containers": ["docker_container_mem"],
                "container_id": "long",
                "interval": 3000,
            },
            {
                "deployment": ("cached", 3000.0),
                "node": [],
                "containers": ["docker_container_mem"],
                "container_id": "long",
            },
        ),
        (
            {
                "node": [],
                "containers": [],
                "container_id": "short",
                "interval": 30,
            },
            {
                "deployment": ("sync", None),
                "node": [],
                "containers": [],
                "container_id": "short",
            },
        ),
        (
            {"deployment": ("cached", 300.0), "node": [], "containers": []},
            {"deployment": ("cached", 300.0), "node": [], "containers": []},
        ),
    ],
)
def test_migrate(value: object, expected: object) -> None:
    assert migrate(value) == expected


def test_migrate_invalid() -> None:
    with pytest.raises(ValueError):
        migrate("unexpected")
