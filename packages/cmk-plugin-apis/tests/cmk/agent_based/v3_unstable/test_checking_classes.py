#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v3_unstable._checking_classes import Metric


def test_metric_name_empty_raises() -> None:
    with pytest.raises(TypeError):
        Metric("", 1.0)


@pytest.mark.parametrize("char", [" ", ":", "/", "\\"])
def test_metric_name_invalid_char_raises(char: str) -> None:
    with pytest.raises(TypeError):
        Metric(f"bad{char}name", 1.0)


def test_metric_name_valid() -> None:
    m = Metric("valid_name", 1.0)
    assert m.name == "valid_name"
