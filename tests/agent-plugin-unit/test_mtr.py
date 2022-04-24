#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import agents.plugins.mtr as mtr


@pytest.mark.parametrize(
    "host, expected_result",
    [
        pytest.param(
            "abc123",
            "abc123",
            id="simple case",
        ),
        pytest.param(
            "abc{123}&%",
            "abc-123",
            id="with funny characters",
        ),
    ],
)
def test_host_to_filename(host, expected_result):
    assert mtr.host_to_filename(host) == expected_result
