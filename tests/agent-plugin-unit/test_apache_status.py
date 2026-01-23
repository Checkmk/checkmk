#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"
# ruff: noqa: I001

import sys
from unittest.mock import Mock

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch
from agents.plugins import apache_status

RESPONSE = "\n".join(("1st line", "2nd line", "3rd line"))


@pytest.fixture
def response():
    return RESPONSE


@pytest.mark.parametrize(
    "cfg",
    [
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
    ],
)
def test_http_cfg_versions(cfg: object) -> None:
    assert apache_status._unpack(cfg) == (("http", None), "127.0.0.1", None, "", "server-status")


@pytest.mark.parametrize(
    "cfg",
    [
        (("https", "/path/to/ca.pem"), "127.0.0.1", 123, ""),
        {
            "protocol": "https",
            "cafile": "/path/to/ca.pem",
            "address": "127.0.0.1",
            "port": 123,
            "instance": "",
        },
    ],
)
def test_https_cfg_versions(cfg: object) -> None:
    assert apache_status._unpack(cfg) == (
        ("https", "/path/to/ca.pem"),
        "127.0.0.1",
        123,
        "",
        "server-status",
    )


@pytest.mark.parametrize(
    "cfg",
    [
        [(("http", None), "127.0.0.1", None, "")],
        [("http", "127.0.0.1", None, "")],
        [("http", "127.0.0.1", None)],
        [("https", "127.0.0.1", None)],
    ],
)
def test_agent(
    cfg: object, response: str, monkeypatch: MonkeyPatch, capsys: CaptureFixture
) -> None:
    monkeypatch.setattr(apache_status, "get_config", lambda: {"servers": cfg, "ssl_ports": [443]})
    monkeypatch.setattr(apache_status, "get_response_body", lambda *args: response)
    apache_status.main()
    captured_stdout = capsys.readouterr()[0]
    assert captured_stdout == (
        "<<<apache_status:sep(124)>>>\n"
        + "\n".join("127.0.0.1|None||%s" % line for line in RESPONSE.split("\n"))
        + "\n"
    )


@pytest.mark.parametrize(
    "scheme",
    ["fax", "file", "ftp", "jar", "snmp", "ssh"],
)
def test_urlopen_illegal_urls(scheme: str) -> None:
    with pytest.raises(ValueError, match="Scheme '%s' is not allowed" % scheme):
        apache_status.get_response_body(scheme, None, "127.0.0.1", "8080", "index.html")


@pytest.mark.parametrize(
    "scheme",
    ["http", "https"],
)
def test_urlopen_legal_urls(scheme: str, mocker: Mock) -> None:
    mocked_urlopen = mocker.patch(
        "agents.plugins.apache_status_2.urlopen"
        if sys.version_info[0] == 2
        else "agents.plugins.apache_status.urlopen"
    )
    apache_status.get_response_body(scheme, None, "127.0.0.1", "8080", "index.html")
    assert mocked_urlopen.call_count == 1  # no assert_called_once() in python < 3.6
