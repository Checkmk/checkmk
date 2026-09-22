#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.livestatus_client._connection import MKLivestatusQueryError
from cmk.livestatus_client.expressions import LqSafe, LqUnsafeValueError
from cmk.livestatus_client.tables import Hosts


def test_lq_unsafe_value_error_is_value_error_and_livestatus_error() -> None:
    with pytest.raises(LqUnsafeValueError) as excinfo:
        LqSafe("a\nb")

    assert isinstance(excinfo.value, ValueError)
    assert isinstance(excinfo.value, MKLivestatusQueryError)


def test_dynamic_column_whitespace_raises_lq_unsafe_value_error() -> None:
    with pytest.raises(LqUnsafeValueError, match="contains whitespace"):
        Hosts.rrddata.dynamic("m1", "load1.max 1 +", 1, 2, 3, 4)
