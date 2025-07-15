#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import livestatus

from cmk.gui import sites
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_intercept_queries(
    mock_livestatus: MockLiveStatusConnection,
    request_context: None,
) -> None:
    with mock_livestatus(expect_status_query=True):
        live = sites.live()

    mock_livestatus.expect_query("GET hosts\nColumns: name")
    with mock_livestatus(expect_status_query=False), livestatus.intercept_queries() as queries:
        live.query("GET hosts\nColumns: name")

    # livestatus.py appends a lot of extra columns, so we only check for startswith
    assert queries[0].startswith("GET hosts\nColumns: name\n")
