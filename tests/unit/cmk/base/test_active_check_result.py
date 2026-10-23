#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the shared active-check result normalization.

This is the seam both the site-local run and the relay run funnel through, so a
check reports the same state and output wherever it ran.
"""

import pytest

from cmk.base.active_check_result import normalize_active_check_result


@pytest.mark.parametrize("code", [0, 1, 2])
def test_nagios_states_pass_through(code: int) -> None:
    state, _ = normalize_active_check_result(code, "output")
    assert state == code


@pytest.mark.parametrize("code", [3, 4, 126, 127, 255, -1])
def test_non_nagios_codes_become_unknown(code: int) -> None:
    state, output = normalize_active_check_result(code, "diagnostic text")
    assert state == 3
    # The plugin's own message survives -- it is the diagnostic.
    assert output == "diagnostic text"


def test_performance_data_is_dropped() -> None:
    _, output = normalize_active_check_result(0, "OK text | rta=0.1ms;;;; pl=0%;;;;")
    assert output == "OK text"


def test_only_first_pipe_matters() -> None:
    _, output = normalize_active_check_result(0, "OK text |a=1|b=2")
    assert output == "OK text"


def test_surrounding_whitespace_is_trimmed() -> None:
    _, output = normalize_active_check_result(0, "  OK text\n")
    assert output == "OK text"


def test_space_before_pipe_is_trimmed() -> None:
    # The space a check leaves in front of the "|" must not reach the output.
    _, output = normalize_active_check_result(0, "OK  |a=1")
    assert output == "OK"


def test_output_without_pipe_is_kept() -> None:
    _, output = normalize_active_check_result(0, "all good here")
    assert output == "all good here"


def test_empty_output_stays_empty() -> None:
    state, output = normalize_active_check_result(0, "")
    assert (state, output) == (0, "")


def test_multiline_output_is_split_at_first_pipe() -> None:
    _, output = normalize_active_check_result(0, "line one\nline two | perf")
    assert output == "line one\nline two"
