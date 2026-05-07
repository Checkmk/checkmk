#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.legacy_checks.bluecat_threads import check_bluecat_threads


def test_make_sure_bluecat_threads_can_handle_new_params_format() -> None:
    results = list(
        check_bluecat_threads(
            {"levels": ("levels", (10, 20))},
            [["1234"]],
        )
    )
    assert results == [
        Result(state=State.CRIT, summary="1234 threads (critical at 20)"),
        Metric("threads", 1234, levels=(10, 20)),
    ]
