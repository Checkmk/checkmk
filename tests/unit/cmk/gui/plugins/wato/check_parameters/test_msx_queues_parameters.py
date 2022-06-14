#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.gui.plugins.wato.check_parameters.msx_queues import transform_msx_queues_inventory

CUSTOMIZED_QUEUES = [("Custom queue", 56)]


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        ([], {}),
        (CUSTOMIZED_QUEUES, {"queue_names": CUSTOMIZED_QUEUES}),
    ],
)
def test_transform_msx_queues_inventory(parameters, expected_result) -> None:
    assert transform_msx_queues_inventory(parameters) == expected_result
