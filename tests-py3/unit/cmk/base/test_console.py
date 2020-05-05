#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import io
import logging

import pytest  # type: ignore[import]

import cmk.base.console as console


@pytest.fixture
def stream():
    return io.StringIO()


def read(stream):
    stream.seek(0)
    return stream.read()


def test_output_without_args(stream):
    console.output("hello", stream=stream)
    assert read(stream) == "hello"


def test_output_with_args(stream):
    console.output("hello %s %i", "bob", 42, stream=stream)
    assert read(stream) == "hello bob 42"


def test_output_with_wrong_args(stream):
    with pytest.raises(TypeError):
        console.output("hello %s %i", "wrong", "args", stream=stream)


def test_output_ignores_stream_errors(stream, mocker, monkeypatch):
    mock = mocker.Mock(side_effect=IOError("bad luck"))
    monkeypatch.setattr(stream, "flush", mock)

    console.output("hello", stream=stream)
    assert read(stream) == "hello"


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
    assert captured.out == "hello"
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


def test_warning(stream):
    console.warning("  hello  ", stream=stream)
    assert read(stream) == console._format_warning("  hello  ")


def test_error(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.error("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert not captured.out
    assert captured.err == "hello"


def test_section_begin(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.section_begin("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert "hello" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err


def test_section_success(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.section_success("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert "hello" in captured.out
    assert "SUCCESS" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err


def test_section_error(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.section_error("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert "hello" in captured.out
    assert "ERROR" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err  # Error on stdout (and not stderr) is not a typo.


def test_step(caplog, capsys):
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    console.step("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert "hello" not in captured.out
    assert "HELLO" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err
