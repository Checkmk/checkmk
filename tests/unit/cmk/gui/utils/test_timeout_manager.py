#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import pytest  # type: ignore[import]

from cmk.gui.utils.timeout_manager import TimeoutManager
from cmk.gui.globals import html
from cmk.gui.exceptions import RequestTimeout


def test_htmllib_integration(register_builtin_html):
    assert html.request.request_timeout == 110

    html.enable_request_timeout()
    html.disable_request_timeout()


def test_timeout_manager_raises_timeout():
    tm = TimeoutManager()

    with pytest.raises(RequestTimeout):
        tm.enable_timeout(1)
        time.sleep(2)


def test_timeout_manager_disable():
    tm = TimeoutManager()

    tm.enable_timeout(1)
    tm.disable_timeout()
    time.sleep(1)
