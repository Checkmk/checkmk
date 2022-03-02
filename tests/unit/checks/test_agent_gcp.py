#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"project": "test", "credentials": "definitely some json", "services": ["gcs", "run"]},
            [
                "--project",
                "test",
                "--credentials",
                "definitely some json",
                "--services",
                "gcs",
                "run",
            ],
            id="minimal case",
        ),
    ],
)
def test_gcp_argument_parsing(
    params: Mapping[str, Any],
    expected_result: Sequence[str],
) -> None:
    assert (
        SpecialAgent("agent_gcp").argument_func(
            params,
            "testhost",
            "address",
        )
        == expected_result
    )
