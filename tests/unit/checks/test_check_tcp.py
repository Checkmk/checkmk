#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        ((1, {}), ["-p", "1", "-H", "$HOSTADDRESS$"]),
    ],
)
def test_check_tcp_argument_parsing(
    params: tuple[float, Mapping[str, object]], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_tcp")
    assert active_check.run_argument_function(params) == expected_args
