#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import contextlib
import logging
import queue
from collections.abc import Iterator, Mapping
from pathlib import Path

from pytest import CaptureFixture

from cmk.utils import log
from cmk.utils.jsontype import JsonSerializable
from cmk.utils.log.security_event import log_security_event, SecurityEvent


@contextlib.contextmanager
def set_log_level(logger: logging.Logger, level: int | str) -> Iterator[None]:
    old_level = logger.level
    logger.setLevel(level)
    yield
    logger.setLevel(old_level)


def test_get_logger() -> None:
    assert logging.getLogger("cmk.asd").parent == log.logger


def test_setup_console_logging(capsys: CaptureFixture[str]) -> None:
    logging.getLogger("cmk.test").info("test123")
    assert ("", "") == capsys.readouterr()

    old_handlers = list(log.logger.handlers)
    try:
        log.setup_console_logging()
        logging.getLogger("cmk.test").warning("test123")
        assert ("test123\n", "") == capsys.readouterr()
    finally:
        log.logger.handlers = old_handlers


def test_set_verbosity() -> None:
    with set_log_level(logging.getLogger("cmk"), logging.INFO):
        l = logging.getLogger("cmk.test_logger")

        assert l.getEffectiveLevel() == logging.INFO
        assert l.isEnabledFor(log.VERBOSE) is False
        assert l.isEnabledFor(logging.DEBUG) is False

        with set_log_level(log.logger, log.verbosity_to_log_level(0)):
            assert l.getEffectiveLevel() == logging.INFO
            assert l.isEnabledFor(log.VERBOSE) is False
            assert l.isEnabledFor(logging.DEBUG) is False

        with set_log_level(log.logger, log.verbosity_to_log_level(1)):
            assert l.getEffectiveLevel() == log.VERBOSE
            assert l.isEnabledFor(log.VERBOSE) is True
            assert l.isEnabledFor(logging.DEBUG) is False

        with set_log_level(log.logger, log.verbosity_to_log_level(2)):
            assert l.getEffectiveLevel() == logging.DEBUG
            assert l.isEnabledFor(log.VERBOSE) is True
            assert l.isEnabledFor(logging.DEBUG) is True

        with set_log_level(log.logger, log.verbosity_to_log_level(3)):
            assert l.getEffectiveLevel() == logging.DEBUG
            assert l.isEnabledFor(log.VERBOSE) is True
            assert l.isEnabledFor(logging.DEBUG) is True


@contextlib.contextmanager
def queue_log_sink(logger: logging.Logger) -> Iterator[queue.Queue[logging.LogRecord]]:
    q: queue.Queue[logging.LogRecord] = queue.Queue()
    queue_handler = logging.handlers.QueueHandler(q)
    logger.addHandler(queue_handler)
    try:
        yield q
    finally:
        logger.removeHandler(queue_handler)


def test_security_event(tmp_path: Path) -> None:
    details: Mapping[str, JsonSerializable] = {"a": ["serialize", "me"], "b": {"b.1": 42.23}}
    event = SecurityEvent("test security event", details, SecurityEvent.Domain.auth)

    logger = logging.getLogger("cmk_security")
    with set_log_level(logger, logging.INFO):
        with queue_log_sink(logger) as log_queue:
            log_security_event(event)
            entry = log_queue.get_nowait()
            assert entry.name == "cmk_security.auth"
            assert (
                entry.getMessage() == '{"summary": "test security event", '
                '"details": {"a": ["serialize", "me"], "b": {"b.1": 42.23}}}'
            )
