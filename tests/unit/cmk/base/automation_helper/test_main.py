#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import multiprocessing
import sys

from cmk.base.automation_helper import (
    _reset_global_multiprocessing_start_method_to_platform_default,
)


def test_reset_global_multiprocessing_start_method_to_platform_default() -> None:
    multiprocessing.set_start_method("forkserver", force=True)
    assert multiprocessing.get_start_method(allow_none=True) == "forkserver"
    _reset_global_multiprocessing_start_method_to_platform_default()
    # Python 3.14 changed the default method, see https://github.com/python/cpython/pull/101556
    assert multiprocessing.get_start_method(allow_none=True) == (
        "forkserver" if sys.version_info >= (3, 14) else "fork"
    )
