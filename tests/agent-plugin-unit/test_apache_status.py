#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access,redefined-outer-name
import sys
import io
import pytest  # type: ignore[import]
from utils import import_module

RESPONSE = "\n".join(("1st line", "2nd line", "3rd line"))


@pytest.fixture(scope="module")
def apache_status():
    return import_module("apache_status")


@pytest.fixture
def response():
    if sys.version_info[0] == 2:
        return io.BytesIO(RESPONSE)
    return io.StringIO(RESPONSE)


@pytest.mark.parametrize("cfg", [
    ("http", "127.0.0.1", None),
    ("http", "127.0.0.1", None, ""),
    (("http", None), "127.0.0.1", None, ""),
    {
        "protocol": "http",
        "cafile": None,
        "address": "127.0.0.1",
        "port": None,
        "instance": "",
    },
])
def test_http_cfg_versions(apache_status, cfg):
    assert apache_status._unpack(cfg) == (("http", None), "127.0.0.1", None, "", "server-status")


@pytest.mark.parametrize("cfg", [
    (("https", "/path/to/ca.pem"), "127.0.0.1", 123, ""),
    {
        "protocol": "https",
        "cafile": "/path/to/ca.pem",
        "address": "127.0.0.1",
        "port": 123,
        "instance": "",
    },
])
def test_https_cfg_versions(apache_status, cfg):
    assert apache_status._unpack(cfg) == (("https", "/path/to/ca.pem"), "127.0.0.1", 123, "",
                                          "server-status")


@pytest.mark.parametrize("cfg", [
    [(("http", None), "127.0.0.1", None, "")],
    [("http", "127.0.0.1", None, "")],
    [("http", "127.0.0.1", None)],
])
def test_agent(apache_status, cfg, response, monkeypatch, capsys):
    monkeypatch.setattr(apache_status, "get_config", lambda: {"servers": cfg, "ssl_ports": [443]})
    monkeypatch.setattr(apache_status, "get_response", lambda *args: response)
    apache_status.main()
    captured_stdout = capsys.readouterr()[0]
    assert captured_stdout == ("<<<apache_status:sep(124)>>>\n" + "\n".join(
        ("127.0.0.1|None||%s" % line for line in RESPONSE.split("\n"))) + "\n")
