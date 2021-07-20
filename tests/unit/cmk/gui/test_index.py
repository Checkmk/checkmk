#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.globals import html, user, local, config
import cmk.gui.main


def test_get_start_url_default(request_context):
    assert cmk.gui.main._get_start_url() == "dashboard.py"


def test_get_start_url_default_config(request_context, monkeypatch):
    monkeypatch.setattr(config, "start_url", "bla.py")
    assert cmk.gui.main._get_start_url() == "bla.py"


def test_get_start_url_user_config(monkeypatch, request_context):
    monkeypatch.setattr(config, "start_url", "bla.py")

    class MockUser:
        @property
        def start_url(self):
            return "user_url.py"

    monkeypatch.setattr(local, "user", MockUser())

    assert cmk.gui.main._get_start_url() == "user_url.py"


def test_get_start_url(request_context):
    start_url = "dashboard.py?name=mein_dashboard"
    html.request.set_var("start_url", start_url)

    assert cmk.gui.main._get_start_url() == start_url


@pytest.mark.parametrize("invalid_url", [
    "http://localhost/",
    "://localhost",
    "javascript:alert(1)",
    "javAscRiPt:alert(1)",
    "localhost:80/bla",
])
def test_get_start_url_invalid(request_context, invalid_url):
    html.request.set_var("start_url", invalid_url)

    assert cmk.gui.main._get_start_url() == "dashboard.py"


def test_get_start_url_invalid_config(monkeypatch, request_context):
    monkeypatch.setattr(user, "_attributes", {
        "start_url": "http://asdasd/",
    })
    assert cmk.gui.main._get_start_url() == "dashboard.py"
