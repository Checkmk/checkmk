#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence

import pytest

from tests.testlib import ActiveCheck


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            (
                "foo",
                {},
            ),
            [
                "$HOSTADDRESS$",
            ],
            id="minimal configuration",
        ),
        pytest.param(
            (
                "foo",
                {"port": 80},
            ),
            [
                "$HOSTADDRESS$",
                "--port",
                80,
            ],
            id="with port",
        ),
        pytest.param(
            (
                "foo",
                {
                    "hosts": ["12.3.4.51", "some-other-host"],
                    "uri": "/some/where",
                    "ssl": True,
                    "timeout": 5,
                    "expect_regex": ".*abc",
                    "form_name": "cool form",
                    "query": "key1=val1&key2=val2",
                    "num_succeeded": (1, 0),
                },
            ),
            [
                "12.3.4.51",
                "some-other-host",
                "--uri",
                "/some/where",
                "--tls",
                "--timeout",
                5,
                "--expected_regex",
                ".*abc",
                "--form_name",
                "cool form",
                "--query_params",
                "key1=val1&key2=val2",
                "--levels",
                1,
                0,
            ],
            id="extensive configuration",
        ),
    ],
)
def test_check_form_submit_argument_parsing(
    params: tuple[str, Mapping[str, object]],
    expected_args: Sequence[object],
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_form_submit")
    assert active_check.run_argument_function(params) == expected_args
