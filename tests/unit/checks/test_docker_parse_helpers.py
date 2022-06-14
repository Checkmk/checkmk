#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.utils.docker as docker

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "indata,expected",
    [
        (
            "docker-pullable://nginx@sha256:e3456c851a152494c3e4ff5fcc26f240206abac0c9d794affb40e0714846c451",
            "e3456c851a15",
        ),
    ],
)
def test_parse_short_id(indata, expected) -> None:
    actual = docker.get_short_id(indata)  # type: ignore[name-defined] # pylint: disable=undefined-variable
    assert actual == expected
