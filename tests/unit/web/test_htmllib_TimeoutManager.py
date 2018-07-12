#!/usr/bin/env python

import time
import pytest

import htmllib
from cmk.gui.exceptions import RequestTimeout

def test_htmllib_integration(register_builtin_html):
    assert html.request.request_timeout == 110

    html.enable_request_timeout()
    html.disable_request_timeout()


def test_timeout_manager_raises_timeout():
    tm = htmllib.TimeoutManager()

    with pytest.raises(RequestTimeout):
        tm.enable_timeout(1)
        time.sleep(2)


def test_timeout_manager_disable():
    tm = htmllib.TimeoutManager()

    tm.enable_timeout(1)
    tm.disable_timeout()
    time.sleep(1)
