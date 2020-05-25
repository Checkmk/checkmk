#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys

if sys.version_info[0] >= 3:
    from io import StringIO as StrIO
else:
    from io import BytesIO as StrIO

import pytest  # type: ignore[import]

from cmk.utils.log import console


@pytest.fixture(name="stream")
def stream_fixture():
    return StrIO()


# HACK: Older Python versions have no easy way to set the terminator in the
# handler, so we remove it here. We switch to Python >= 3.7 soon, anyway...
def strip_newline_hack(s):
    return s if sys.version_info > (3, 2) else s[:-1]


def read(stream):
    stream.seek(0)
    return strip_newline_hack(stream.read())


def test_verbose_on(stream, caplog):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.verbose("hello", stream=stream)
    assert read(stream) == "hello"


def test_verbose_off(stream, caplog):
    caplog.set_level(console.VERBOSE + 1, logger="cmk.base")

    console.verbose("hello", stream=stream)
    assert not read(stream)


def test_verbose_default_stream_on(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.verbose("hello")

    captured = capsys.readouterr()
    assert strip_newline_hack(captured.out) == "hello"
    assert not captured.err


def test_verbose_default_stream_off(caplog, capsys):
    caplog.set_level(console.VERBOSE + 1, logger="cmk.base")

    console.verbose("hello")

    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


def test_vverbose_on(stream, caplog):
    caplog.set_level(logging.DEBUG, logger="cmk.base")

    console.vverbose("hello", stream=stream)
    assert read(stream) == "hello"


def test_vverbose_off(stream, caplog):
    caplog.set_level(logging.DEBUG + 1, logger="cmk.base")

    console.vverbose("hello", stream=stream)
    assert not read(stream)


def test_info_on(stream, caplog):
    caplog.set_level(logging.INFO, logger="cmk.base")

    console.info("hello", stream=stream)
    assert read(stream) == "hello"


def test_info_off(stream, caplog):
    caplog.set_level(logging.INFO + 1, logger="cmk.base")

    console.info("hello", stream=stream)
    assert not read(stream)


def test_warning(stream):
    console.warning("  hello  ", stream=stream)
    assert read(stream) == console._format_warning("  hello  ")


def test_error(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.error("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert not captured.out
    assert strip_newline_hack(captured.err) == "hello"
