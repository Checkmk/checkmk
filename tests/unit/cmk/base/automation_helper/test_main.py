#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import multiprocessing

from cmk.base.automation_helper import (
    _reset_global_multiprocessing_start_method_to_platform_default,
)


def test_reset_global_multiprocessing_start_method_to_platform_default() -> None:
    multiprocessing.set_start_method("forkserver", force=True)
    assert multiprocessing.get_start_method(allow_none=True) == "forkserver"
    _reset_global_multiprocessing_start_method_to_platform_default()
    # will fail from Python 3.14 onwards because then, the default method will be "spawn" also on Unix
    assert multiprocessing.get_start_method(allow_none=True) == "fork"
