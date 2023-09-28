#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import logging

import pytest

from cmk.utils.log import console


@pytest.fixture(name="stream")
def stream_fixture() -> io.StringIO:
    return io.StringIO()


def read(stream: io.StringIO) -> str:
    stream.seek(0)
    return stream.read()


def test_verbose_on(stream: io.StringIO, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.verbose("hello", stream=stream)
    assert read(stream) == "hello"


def test_verbose_off(stream: io.StringIO, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(console.VERBOSE + 1, logger="cmk.base")

    console.verbose("hello", stream=stream)
    assert not read(stream)


def test_verbose_default_stream_on(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.verbose("hello")

    captured = capsys.readouterr()
    assert captured.out == "hello"
    assert not captured.err


def test_verbose_default_stream_off(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(console.VERBOSE + 1, logger="cmk.base")

    console.verbose("hello")

    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_vverbose_on(stream: io.StringIO, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="cmk.base")

    console.vverbose("hello", stream=stream)
    assert read(stream) == "hello"


def test_vverbose_off(stream: io.StringIO, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG + 1, logger="cmk.base")

    console.vverbose("hello", stream=stream)
    assert not read(stream)


def test_info_on(stream: io.StringIO, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="cmk.base")

    console.info("hello", stream=stream)
    assert read(stream) == "hello"


def test_info_off(stream: io.StringIO, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO + 1, logger="cmk.base")

    console.info("hello", stream=stream)
    assert not read(stream)


def test_warning(stream: io.StringIO) -> None:
    console.warning("  hello  ", stream=stream)
    assert read(stream) == console._format_warning("  hello  ")


def test_error(caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.error("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert not captured.out
    assert captured.err == "hello"
