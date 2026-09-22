#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# ruff: noqa: RUF100
# ruff: noqa: I001

import os
from typing import Sequence

import pytest
from _pytest.monkeypatch import MonkeyPatch

from agents.plugins import mtr


@pytest.mark.parametrize(
    "host, expected_result",
    [
        pytest.param(
            "abc123",
            "abc123",
            id="simple case",
        ),
        pytest.param(
            "abc{123}&%",
            "abc-123",
            id="with funny characters",
        ),
    ],
)
def test_host_to_filename(host: str, expected_result: str) -> None:
    assert mtr.host_to_filename(host) == expected_result


GOOD_REPORT = [
    "1451228358\n",
    "Start: Sun Dec 27 14:35:18 2015\n",
    "HOST: purple         Loss%   Snt   Last   Avg  Best  Wrst StDev\n",
    " 1.|-- 80.69.76.120    0.0%    10    0.3   0.4   0.3   0.6   0.0\n",
    "  |  `|-- 129.250.2.159\n",
    " 2.|-- 80.249.209.100  0.0%    10    1.0   1.1   0.8   1.4   0.0\n",
]


def test_parse_report_lines_success() -> None:
    lasttime, hops, error = mtr.parse_report_lines(GOOD_REPORT)
    assert lasttime == 1451228358
    assert error is None
    assert hops == {
        1: {
            "hopname": "80.69.76.120",
            "loss": "0.0%",
            "snt": "10",
            "last": "0.3",
            "avg": "0.4",
            "best": "0.3",
            "wrst": "0.6",
            "stddev": "0.0",
        },
        2: {
            "hopname": "80.249.209.100",
            "loss": "0.0%",
            "snt": "10",
            "last": "1.0",
            "avg": "1.1",
            "best": "0.8",
            "wrst": "1.4",
            "stddev": "0.0",
        },
    }


@pytest.mark.parametrize(
    "lines, expected_error",
    [
        pytest.param(
            [
                "1451228358\n",
                "mtr: Failed to resolve host: broken.example.com: Name or service not known\n",
            ],
            "mtr: Failed to resolve host: broken.example.com: Name or service not known",
            id="mtr wrote its complaint into the report",
        ),
        pytest.param(
            ["1451228358\n", "mtr: Unable to get raw sockets.\n", "\n"],
            "mtr: Unable to get raw sockets.",
            id="blank lines do not count",
        ),
        pytest.param(
            [
                "1451228358\n",
                "Start: Sun Dec 27 14:35:18 2015\n",
                "HOST: purple         Loss%   Snt   Last   Avg  Best  Wrst StDev\n",
            ],
            "report contains no hop",
            id="report layout without a single hop",
        ),
        pytest.param([], "report has no time stamp", id="empty report"),
    ],
)
def test_parse_report_lines_error(lines: Sequence[str], expected_error: str) -> None:
    _lasttime, hops, error = mtr.parse_report_lines(lines)
    assert not hops
    assert error == expected_error


def test_sanitized_error_survives_the_separator() -> None:
    assert mtr.sanitized_error(["mtr: bad |pipe|\n", "  and a second line\n"]) == (
        "mtr: bad /pipe/ and a second line"
    )


def test_sanitized_error_is_truncated() -> None:
    error = mtr.sanitized_error(["x" * 500])
    assert len(error) == mtr.max_error_length
    assert error.endswith("...")


@pytest.mark.parametrize(
    "error, expected_trailer",
    [
        pytest.param(None, "", id="no error"),
        pytest.param("", "", id="empty error"),
        pytest.param(
            "mtr: Unable to get raw sockets.", "|**ERROR**|mtr: Unable to get raw sockets."
        ),
    ],
)
def test_error_trailer(error: str, expected_trailer: str) -> None:
    assert mtr.error_trailer(error) == expected_trailer


@pytest.mark.parametrize(
    "fields, expected_error",
    [
        pytest.param([], None, id="nothing behind the hops"),
        pytest.param(["**ERROR**"], None, id="marker without a message"),
        pytest.param(["something", "else"], None, id="no marker"),
        pytest.param(["**ERROR**", "mtr: boom\n"], "mtr: boom", id="marker and message"),
    ],
)
def test_error_from_trailer(fields: Sequence[str], expected_error: str) -> None:
    assert mtr.error_from_trailer(fields) == expected_error


def test_error_survives_a_status_file_round_trip(tmpdir: object, monkeypatch: MonkeyPatch) -> None:
    """An error has to outlive the run that saw it - mtr is not restarted every time."""
    monkeypatch.setattr(mtr, "status_filename", os.path.join(str(tmpdir), "mtr.state"))
    status = {
        "broken.example.com": {"hops": {}, "lasttime": 1758196800, "error": "mtr: boom"},
        "fine.example.com": {
            "hops": {
                1: {
                    "hopname": "1.2.3.4",
                    "loss": "0.0%",
                    "snt": "10",
                    "last": "1.3",
                    "avg": "2.2",
                    "best": "1.2",
                    "wrst": "7.0",
                    "stddev": "1.6",
                }
            },
            "lasttime": 1758196800,
        },
    }
    mtr.save_status(status)
    restored = mtr.read_status()
    assert restored["broken.example.com"]["error"] == "mtr: boom"
    assert "error" not in restored["fine.example.com"]
    assert restored["fine.example.com"]["hops"] == status["fine.example.com"]["hops"]


@pytest.mark.parametrize(
    "host, expected_result",
    [
        pytest.param("www.google.com", "www.google.com", id="plain host name"),
        pytest.param("192.168.1.1", "192.168.1.1", id="IPv4 address"),
        pytest.param("2001:db8::1", "2001:db8::1", id="IPv6 address"),
        pytest.param("foo.example.com (IPv6)", "foo.example.com", id="with derived suffix"),
        pytest.param(
            "2001:db8::1 (TCP port 8080)", "2001:db8::1", id="suffix built from several settings"
        ),
    ],
)
def test_mtr_target(host: str, expected_result: str) -> None:
    assert mtr.mtr_target(host) == expected_result
