#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import logging
import re
from collections.abc import Iterator

import pytest

from cmk.server_side_programs.v1 import configure_logging


@pytest.fixture(name="root_logger")
def _root_logger() -> Iterator[logging.Logger]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield root
    root.handlers[:] = handlers
    root.setLevel(level)


def test_records_from_the_level_up_are_written_to_stderr_in_the_checkmk_log_format(
    root_logger: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    root_logger.handlers.clear()
    configure_logging(logging.INFO)

    logging.getLogger("cmk.plugins.myagent").debug("the dropped message")
    logging.getLogger("cmk.plugins.myagent").info("the message")

    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2} "
        r"\[cmk\.plugins\.myagent\] \[INFO\] the message\n",
        capsys.readouterr().err,
    )


def test_replaces_the_logging_configuration_already_in_place(
    root_logger: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    previous_stream = io.StringIO()
    root_logger.handlers[:] = [logging.StreamHandler(previous_stream)]
    configure_logging(logging.INFO)

    logging.getLogger("cmk.plugins.myagent").warning("the message")

    assert not previous_stream.getvalue()
    assert capsys.readouterr().err.endswith(" [cmk.plugins.myagent] [WARNING] the message\n")


def test_below_info_writes_where_the_record_was_logged(
    root_logger: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    root_logger.handlers.clear()
    configure_logging(logging.DEBUG)

    logging.getLogger("cmk.plugins.myagent").debug("the message")

    assert re.fullmatch(
        r"\S+ \S+ \[cmk\.plugins\.myagent test_logging\.py:\d+ "
        r"test_below_info_writes_where_the_record_was_logged\] \[DEBUG\] the message\n",
        capsys.readouterr().err,
    )
