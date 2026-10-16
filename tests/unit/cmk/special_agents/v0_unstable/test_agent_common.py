#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress

import pytest

from cmk.special_agents.v0_unstable.agent_common import _special_agent_main_core


def _parse_arguments(debug: bool) -> argparse.Namespace:
    return argparse.Namespace(debug=debug, verbose=0)


def _write_section(_args: argparse.Namespace) -> int:
    sys.stdout.write("<<<section>>>\n")
    sys.stdout.flush()
    return 0


def _reset_connection(_args: argparse.Namespace) -> int:
    raise BrokenPipeError(32, "Broken pipe")


@contextmanager
def _stdout_pipe(*, reader_open: bool) -> Iterator[None]:
    # Not a fixture: pytest's capturing replaces sys.stdout again after fixture setup.
    read_fd, write_fd = os.pipe()
    if not reader_open:
        os.close(read_fd)
    stdout, sys.stdout = sys.stdout, os.fdopen(write_fd, "w")
    try:
        yield
    finally:
        with suppress(BrokenPipeError):
            sys.stdout.close()
        sys.stdout = stdout
        if reader_open:
            os.close(read_fd)


def _run(main_fn: Callable[[argparse.Namespace], int], *, debug: bool = False) -> int:
    return _special_agent_main_core(lambda _argv: _parse_arguments(debug), main_fn, [])


def test_special_agent_main_core_stdout_reader_gone_skips_crash_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _stdout_pipe(reader_open=False):
        assert _run(_write_section) == 1
    stderr = capsys.readouterr().err
    assert stderr.rstrip().endswith("BrokenPipeError: [Errno 32] Broken pipe")
    assert "Agent failed" not in stderr


def test_special_agent_main_core_other_broken_pipe_creates_crash_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _stdout_pipe(reader_open=True):
        assert _run(_reset_connection) == 1
    assert "Agent failed" in capsys.readouterr().err


def test_special_agent_main_core_stdout_reader_gone_reraises_in_debug_mode() -> None:
    with _stdout_pipe(reader_open=False), pytest.raises(BrokenPipeError):
        _run(_write_section, debug=True)
