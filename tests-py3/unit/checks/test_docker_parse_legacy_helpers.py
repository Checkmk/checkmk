#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks

exec(open(os.path.join(os.path.dirname(__file__), '../../../checks/legacy_docker.include')).read())


@pytest.mark.parametrize('indata,outdata', [
    ("123GB (42%)", 123000000000),
    ("0 B", 0),
    ("2B", 2),
    ("23 kB", 23000),
    ("", None),
])
def test_parse_legacy_docker_get_bytes(indata, outdata):
    parsed = _legacy_docker_get_bytes(indata)  # pylint: disable=undefined-variable
    assert outdata == parsed


@pytest.mark.parametrize('indata,outdata', [
    ("sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817", "8b15606a9e3e"),
])
def test_parse_legacy_docker_trunk_id(indata, outdata):
    parsed = _legacy_docker_trunk_id(indata)  # pylint: disable=undefined-variable
    assert outdata == parsed
