#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.lib.rabbitmq import discover_key


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param({}, [], id="no service"),
        pytest.param(
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 431, "proc_total": 1048576},
                }
            },
            [Service(item="rabbit@my-rabbit")],
            id="service",
        ),
    ],
)
def test_discover_proc(section: Mapping[str, Any], expected: Iterable[Service]) -> None:
    assert list(discover_key("proc")(section)) == expected
