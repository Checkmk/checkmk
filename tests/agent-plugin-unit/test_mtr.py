#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# ruff: noqa: RUF100
# ruff: noqa: I001

import pytest
from agents.plugins import mtr


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
def test_host_to_filename(host: str, expected_result: str) -> None:
    assert mtr.host_to_filename(host) == expected_result
