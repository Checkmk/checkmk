#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys

from pytest import CaptureFixture, LogCaptureFixture

from cmk.utils.log import console


def test_verbose_on(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")
    console.verbose("hello")
    assert ("hello\n", "") == capsys.readouterr()


def test_verbose_off(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(console.VERBOSE + 1, logger="cmk.base")
    console.verbose("hello")
    assert ("", "") == capsys.readouterr()


def test_verbose_default_stream_on(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")
    console.verbose("hello")
    assert ("hello\n", "") == capsys.readouterr()


def test_verbose_default_stream_off(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(console.VERBOSE + 1, logger="cmk.base")
    console.verbose("hello")
    assert ("", "") == capsys.readouterr()


def test_debug_on(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(logging.DEBUG, logger="cmk.base")
    console.debug("hello")
    assert ("hello\n", "") == capsys.readouterr()


def test_debug_off(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(logging.DEBUG + 1, logger="cmk.base")
    console.debug("hello")
    assert ("", "") == capsys.readouterr()


def test_info_on(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(logging.INFO, logger="cmk.base")
    console.info("hello")
    assert ("hello\n", "") == capsys.readouterr()


def test_info_off(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(logging.INFO + 1, logger="cmk.base")
    console.info("hello")
    assert ("", "") == capsys.readouterr()


def test_warning(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    console.warning("  hello  ", file=sys.stderr)
    assert ("", "  hello  \n") == capsys.readouterr()


def test_error(caplog: LogCaptureFixture, capsys: CaptureFixture[str]) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")
    console.error("hello", file=sys.stderr)
    assert ("", "hello\n") == capsys.readouterr()
