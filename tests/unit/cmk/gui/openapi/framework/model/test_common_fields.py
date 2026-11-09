#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.openapi.framework.model.common_fields import timerange_from_internal


@pytest.mark.usefixtures("request_context")
@pytest.mark.xfail(strict=True, raises=ValueError, reason="crash group 4787")
def test_a_duration_that_is_no_graph_time_range_anymore_becomes_an_age() -> None:
    assert timerange_from_internal(12345) == timerange_from_internal(("age", 12345))
