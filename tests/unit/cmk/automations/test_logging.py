#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import logging
from pathlib import Path

import pytest

from cmk.automations.logging import LoggingManager, VERBOSE


def test_verbose_level_is_registered() -> None:
    assert VERBOSE == 15
    assert logging.getLevelName(VERBOSE) == "VERBOSE"


def test_init_sets_level_on_cmk_logger() -> None:
    manager = LoggingManager(log_level=logging.DEBUG)
    assert manager.get_logger().name == "cmk"
    assert manager.get_logger().level == logging.DEBUG


def test_get_logger_returns_cmk_logger_by_default() -> None:
    manager = LoggingManager()
    assert manager.get_logger() is manager.get_logger("cmk")


def test_get_logger_returns_child_logger() -> None:
    manager = LoggingManager()
    child = manager.get_logger("cmk.base")
    assert child.name == "cmk.base"
    assert child.parent is manager.get_logger()


def test_get_logger_strips_cmk_prefix() -> None:
    manager = LoggingManager()
    # Names with and without the "cmk." prefix point at the same child logger.
    assert manager.get_logger("cmk.foo") is manager.get_logger("foo")


def test_stream_logging_emits_records() -> None:
    manager = LoggingManager(log_level=logging.DEBUG)
    stream = io.StringIO()

    with manager.stream_logging(stream=stream, log_level=logging.WARNING):
        manager.get_logger().warning("danger")

    assert stream.getvalue() == "danger\n"


def test_stream_logging_respects_handler_level() -> None:
    manager = LoggingManager(log_level=logging.DEBUG)
    stream = io.StringIO()

    with manager.stream_logging(stream=stream, log_level=logging.WARNING):
        manager.get_logger().info("ignored")

    assert stream.getvalue() == ""


def test_stream_logging_removes_handler_on_exit() -> None:
    manager = LoggingManager()
    logger = manager.get_logger()
    handlers_before = list(logger.handlers)

    with manager.stream_logging(stream=io.StringIO()):
        assert len(logger.handlers) == len(handlers_before) + 1

    assert logger.handlers == handlers_before


def test_file_logging_writes_to_file(tmp_path: Path) -> None:
    manager = LoggingManager(log_level=logging.DEBUG)
    log_file = tmp_path / "cmk.log"

    with manager.file_logging(path=log_file, log_level=logging.INFO):
        manager.get_logger().info("hello file")

    content = log_file.read_text(encoding="utf-8")
    assert "hello file" in content
    assert f"[{logging.INFO}]" in content
    assert "[cmk]" in content


def test_file_logging_removes_handler_on_exit(tmp_path: Path) -> None:
    manager = LoggingManager()
    logger = manager.get_logger()
    handlers_before = list(logger.handlers)

    with manager.file_logging(path=tmp_path / "cmk.log"):
        assert len(logger.handlers) == len(handlers_before) + 1

    assert logger.handlers == handlers_before


def test_temporary_log_level() -> None:
    manager = LoggingManager(log_level=logging.DEBUG)
    stream = io.StringIO()

    with manager.stream_logging(stream=stream, log_level=logging.NOTSET):
        logger = manager.get_logger()
        logger.info("hello file")

        with manager.temporary_log_level(log_level=logging.CRITICAL):
            logging.info("Danger, Will Robinson!")

        logger.info("bye file")

        assert stream.getvalue() == "hello file\nbye file\n"


def test_temporary_log_level_restores_previous_level() -> None:
    manager = LoggingManager(log_level=logging.WARNING)

    with manager.temporary_log_level(logging.DEBUG):
        assert manager.get_logger().level == logging.DEBUG

    assert manager.get_logger().level == logging.WARNING


@pytest.mark.parametrize("name", ["cmk", "cmk.base.checkers", "base.checkers"])
def test_get_logger_accepts_various_names(name: str) -> None:
    manager = LoggingManager()
    assert manager.get_logger(name).name.startswith("cmk")


def test_nesting_handlers(tmp_path: Path) -> None:
    manager = LoggingManager(log_level=logging.DEBUG)
    stream = io.StringIO()
    log_file = tmp_path / "cmk.log"
    with (
        manager.file_logging(path=log_file, log_level=logging.INFO),
        manager.stream_logging(stream=stream, log_level=logging.ERROR),
    ):
        logger = manager.get_logger()
        logger.debug("DEBUG message")
        logger.info("INFO message")
        logger.warning("WARNING message")
        logger.error("ERROR message")

    assert stream.getvalue() == "ERROR message\n"

    logged_lines = log_file.read_text(encoding="utf-8").splitlines()
    for level in ("INFO", "WARNING", "ERROR"):
        assert any(f"{level} message" in line for line in logged_lines)
    assert all("DEBUG message" not in line for line in logged_lines)
