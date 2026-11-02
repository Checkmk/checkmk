#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.licensing.helper import get_licensing_logger, init_logging_if_missing


@pytest.fixture(name="licensing_logger")
def fixture_licensing_logger() -> Iterator[logging.Logger]:
    """The licensing logger of this process, with its handlers restored after the test."""
    logger = get_licensing_logger()
    handlers, propagate = logger.handlers[:], logger.propagate
    yield logger
    for handler in logger.handlers:
        if handler not in handlers:
            handler.close()
    logger.handlers[:] = handlers
    logger.propagate = propagate


def test_log_handler_is_set_up_once(licensing_logger: logging.Logger, tmp_path: Path) -> None:
    init_logging_if_missing(tmp_path)
    handlers = licensing_logger.handlers[:]

    init_logging_if_missing(tmp_path)

    assert licensing_logger.handlers == handlers


@pytest.mark.usefixtures("licensing_logger")
def test_log_handler_follows_another_log_directory(tmp_path: Path) -> None:
    init_logging_if_missing(tmp_path / "old")

    init_logging_if_missing(tmp_path / "new").warning("a message")

    assert "a message" in (tmp_path / "new" / "licensing.log").read_text()
    assert "a message" not in (tmp_path / "old" / "licensing.log").read_text()


@pytest.mark.usefixtures("licensing_logger")
def test_deleted_log_file_is_created_again(tmp_path: Path) -> None:
    logger = init_logging_if_missing(tmp_path)
    (tmp_path / "licensing.log").unlink()

    logger.warning("a message")

    assert "a message" in (tmp_path / "licensing.log").read_text()


@pytest.mark.usefixtures("licensing_logger")
def test_log_file_created_again_by_another_process_is_written(tmp_path: Path) -> None:
    logger = init_logging_if_missing(tmp_path)
    (tmp_path / "licensing.log").unlink()
    (tmp_path / "licensing.log").touch()

    logger.warning("a message")

    assert "a message" in (tmp_path / "licensing.log").read_text()
