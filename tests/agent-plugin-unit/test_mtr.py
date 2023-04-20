#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import pytest

if sys.version_info[0] == 2:
    import agents.plugins.mtr_2 as mtr  # pylint: disable=syntax-error
else:
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
def test_host_to_filename(host, expected_result) -> None:  # type: ignore[no-untyped-def]
    assert mtr.host_to_filename(host) == expected_result
