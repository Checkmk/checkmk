#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "max_surge,total,expected",
    [
        (1, 4, 6),
        ("25%", 10, 14),
    ],
)
def test_surge_levels(max_surge, total, expected):
    check = Check("k8s_replicas")
    crit = check.context["parse_k8s_surge"](max_surge, total)
    assert crit == expected


@pytest.mark.parametrize(
    "max_unavailable,total,expected",
    [
        (2, 5, 3),
        ("25%", 10, 7),
    ],
)
def test_unavailability_levels(max_unavailable, total, expected):
    check = Check("k8s_replicas")
    crit_lower = check.context["parse_k8s_unavailability"](max_unavailable, total)
    assert crit_lower == expected
