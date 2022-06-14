#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from tests.testlib import on_time

import cmk.utils.log as log


def test_get_logger() -> None:
    l = logging.getLogger("cmk.asd")
    assert l.parent == log.logger


def test_setup_console_logging(capsys) -> None:
    out, err = capsys.readouterr()
    log.clear_console_logging()

    assert out == ""
    assert err == ""

    logging.getLogger("cmk.test").info("test123")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    log.setup_console_logging()
    l = logging.getLogger("cmk.test")
    l.info("test123")

    # Cleanup handler registered with log.setup_console_logging()
    log.logger.handlers.pop()

    out, err = capsys.readouterr()
    assert out == "test123\n"
    assert err == ""


def test_open_log(tmp_path) -> None:
    log_file = tmp_path / "test.log"
    log.open_log(log_file)

    with on_time("2018-04-15 16:50", "CET"):
        log.logger.warning("abc")
        log.logger.warning("äbc")

    with log_file.open("rb") as f:
        assert f.read() == (
            b"2018-04-15 18:50:00,000 [30] [cmk] abc\n"
            b"2018-04-15 18:50:00,000 [30] [cmk] \xc3\xa4bc\n"
        )


def test_set_verbosity() -> None:
    root = logging.getLogger("cmk")
    root.setLevel(logging.INFO)

    l = logging.getLogger("cmk.test_logger")
    assert l.getEffectiveLevel() == logging.INFO
    assert l.isEnabledFor(log.VERBOSE) is False
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(0))
    assert l.getEffectiveLevel() == logging.INFO
    assert l.isEnabledFor(log.VERBOSE) is False
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(1))
    assert l.getEffectiveLevel() == log.VERBOSE
    assert l.isEnabledFor(log.VERBOSE) is True
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(2))
    assert l.getEffectiveLevel() == logging.DEBUG
    assert l.isEnabledFor(log.VERBOSE) is True
    assert l.isEnabledFor(logging.DEBUG) is True

    # Use debug level (highest supported)
    log.logger.setLevel(log.verbosity_to_log_level(3))
    assert l.getEffectiveLevel() == logging.DEBUG
    assert l.isEnabledFor(log.VERBOSE) is True
    assert l.isEnabledFor(logging.DEBUG) is True

    # Reset verbosity for next test run.
    log.logger.setLevel(log.verbosity_to_log_level(0))
