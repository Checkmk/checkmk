#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import io

import pytest

import cmk.base.obsolete_output as out


@pytest.fixture
def stream():
    return io.StringIO()


def read(stream):
    stream.seek(0)
    return stream.read()


def test_output_without_args(stream) -> None:
    out.output("hello", stream=stream)
    assert read(stream) == "hello"


def test_output_with_args(stream) -> None:
    out.output("hello %s %i", "bob", 42, stream=stream)
    assert read(stream) == "hello bob 42"


def test_output_with_wrong_args(stream) -> None:
    with pytest.raises(TypeError):
        out.output("hello %s %i", "wrong", "args", stream=stream)


def test_output_ignores_stream_errors(stream, mocker, monkeypatch) -> None:
    mock = mocker.Mock(side_effect=IOError("bad luck"))
    monkeypatch.setattr(stream, "flush", mock)

    out.output("hello", stream=stream)
    assert read(stream) == "hello"
