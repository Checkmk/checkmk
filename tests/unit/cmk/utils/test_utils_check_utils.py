#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.check_utils import (
    ActiveCheckResult,
    unwrap_parameters,
    worst_service_state,
    wrap_parameters,
)


@pytest.mark.parametrize(
    "params",
    [
        "foo_levels",
        (1, 2),
        {"levels": (1, 2)},
    ],
)
def test_un_wrap_parameters(params) -> None:
    wrapped = wrap_parameters(params)
    assert isinstance(wrapped, dict)
    assert unwrap_parameters(wrapped) == params


def test_noop_wrap_parameters() -> None:
    assert {"levels": (1, 2)} == wrap_parameters({"levels": (1, 2)})


def test_noop_unwrap_parameters() -> None:
    assert {"levels": (1, 2)} == unwrap_parameters({"levels": (1, 2)})


def test_worst_service_state_ok() -> None:
    assert worst_service_state(0, 0, default=0) == 0


def test_worst_service_state_warn() -> None:
    assert worst_service_state(0, 1, default=0) == 1


def test_worst_service_state_crit() -> None:
    assert worst_service_state(0, 1, 2, 3, default=0) == 2


def test_worst_service_state_unknown() -> None:
    assert worst_service_state(0, 1, 3, default=0) == 3


def test_worst_service_state_empty() -> None:
    assert worst_service_state(default=0) == 0
    assert worst_service_state(default=1) == 1
    assert worst_service_state(default=2) == 2
    assert worst_service_state(default=3) == 3


def test_active_check_result() -> None:

    assert ActiveCheckResult.from_subresults(
        ActiveCheckResult(0, "Ok", ("We're good",), ("metric1",)),
        ActiveCheckResult(2, "Critical", ("We're doomed",), ("metric2",)),
    ) == ActiveCheckResult(
        2, "Ok, Critical(!!)", ["We're good", "We're doomed(!!)"], ["metric1", "metric2"]
    )
