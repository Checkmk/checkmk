#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.log import console

import cmk.base.section as section


def test_section_begin(caplog, capsys) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    section.section_begin("hello")

    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err


def test_section_success(caplog, capsys) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    section.section_success("hello")

    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert "SUCCESS" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err


def test_section_error(caplog, capsys) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    section.section_error("hello")

    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert "ERROR" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err  # Error on stdout (and not stderr) is not a typo.


def test_section_step(caplog, capsys) -> None:
    caplog.set_level(console.VERBOSE, logger="cmk.base")

    section.section_step("hello")

    captured = capsys.readouterr()  # no `stream` arg
    assert "hello" not in captured.out
    assert "HELLO" in captured.out
    assert captured.out.endswith("\n")
    assert not captured.err
