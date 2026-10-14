#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.http import request
from cmk.gui.session import session
from cmk.gui.views.page_ajax_reschedule import PageRescheduleCheck


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_reschedule_rejects_a_host_not_visible_to_the_user(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    request.set_var("site", "NO_SITE")
    request.set_var("host", "host-secret")
    request.set_var("_csrf_token", session.session_info.csrf_token)
    mock_livestatus.expect_query(
        "GET hosts\nColumns: host_name\nFilter: host_name = host-secret", sites=["NO_SITE"]
    )

    with mock_livestatus, pytest.raises(MKGeneralException, match="not found"):
        PageRescheduleCheck().page()
