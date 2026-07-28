#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.docker.rulesets.mk_docker_container_piggybacked import migrate


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, {"deployment": ("do_not_deploy", None)}),
        ({}, {"deployment": ("sync", None)}),
        ({"interval": 30}, {"deployment": ("sync", None)}),
        ({"interval": 60}, {"deployment": ("sync", None)}),
        ({"interval": 300}, {"deployment": ("cached", 300.0)}),
        (
            {"deployment": ("sync", None)},
            {"deployment": ("sync", None)},
        ),
        (
            {"deployment": ("do_not_deploy", None)},
            {"deployment": ("do_not_deploy", None)},
        ),
        (
            {"deployment": ("cached", 600.0)},
            {"deployment": ("cached", 600.0)},
        ),
    ],
)
def test_migrate(value: object, expected: object) -> None:
    assert migrate(value) == expected
