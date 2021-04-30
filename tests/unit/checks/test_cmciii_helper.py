#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from testlib import Check  # type: ignore[import]
import pytest


@pytest.mark.parametrize("variable_splitted, expected", [
    (["one", "two"], ["loc", "one", ""]),
    (["one", "two", "three"], ["loc", "one", "two"]),
    (["Phase", "two"], ["loc", "", "Phase", ""]),
    (["Phase", "two", "three"], ["loc", "", "Phase", "two"]),
])
def test_cmciii_container(variable_splitted, expected):
    cmciii_container = Check('cmciii').context['cmciii_container']
    assert cmciii_container("loc", variable_splitted) == expected


@pytest.mark.parametrize("variable_splitted", [
    [],
    ["one"],
])
def test_cmciii_container_raises(variable_splitted):
    cmciii_container = Check('cmciii').context['cmciii_container']
    with pytest.raises(IndexError):
        cmciii_container("loc", variable_splitted)
