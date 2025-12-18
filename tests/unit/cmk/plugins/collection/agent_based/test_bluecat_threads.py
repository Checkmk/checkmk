#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.bluecat_threads import check_bluecat_threads, parse_bluecat_threads


def test_make_sure_bluecat_threads_can_handle_new_params_format() -> None:
    assert list(
        check_bluecat_threads(
            None,
            {"levels": ("levels", (10, 20))},
            parse_bluecat_threads([["1234"]]),
        )
    ) == [(2, "1234 (warn/crit at 10/20)", [("threads", 1234.0, 10.0, 20.0, 0.0, None)])]
