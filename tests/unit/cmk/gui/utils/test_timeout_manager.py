#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import signal
import time

import pytest
from flask import Flask

from cmk.gui import http
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.http import request
from cmk.gui.utils.timeout_manager import TimeoutManager


@pytest.mark.skip(reason="flaky - see resilience test run 6851")
def test_timeout_registered_and_unregistered_by_checkmk_flask_app(flask_app: Flask) -> None:
    assert signal.getsignal(signal.SIGALRM) is signal.SIG_DFL
    assert request.request_timeout == 110
    assert signal.alarm(0) == 0

    with flask_app.test_request_context("/NO_SITE/check_mk/login.py"):
        flask_app.preprocess_request()
        assert callable(signal.getsignal(signal.SIGALRM))
        assert request.request_timeout == 110
        assert signal.alarm(0) == 110
        flask_app.process_response(http.Response())

    assert signal.getsignal(signal.SIGALRM) is signal.SIG_DFL
    assert request.request_timeout == 110
    assert signal.alarm(0) == 0


def test_timeout_manager_raises_timeout() -> None:
    tm = TimeoutManager()

    with pytest.raises(RequestTimeout):
        tm.enable_timeout(1)
        time.sleep(2)


def test_timeout_manager_disable() -> None:
    tm = TimeoutManager()

    tm.enable_timeout(1)
    tm.disable_timeout()
    time.sleep(1)
