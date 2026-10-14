#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.views.page_ajax_reschedule import PageRescheduleCheck
from cmk.livestatus_client.testing import MockLiveStatusConnection


class _RequestReturning:
    def __init__(self, api_request: dict[str, object]) -> None:
        self._api_request = api_request
        self.remote_ip = "127.0.0.1"

    def get_request(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return self._api_request

    def get_str_input(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_reschedule_rejects_a_host_not_visible_to_the_user(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    page_request = _RequestReturning(
        {
            "site": "NO_SITE",
            "host": "host-secret",
            "_csrf_token": session.session_info.csrf_token,
        }
    )
    ctx = PageContext(
        config=load_config,
        request=cast(Request, page_request),
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(load_config, all_permissions()),
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: host_name\nFilter: host_name = host-secret", sites=["NO_SITE"]
    )

    with mock_livestatus, pytest.raises(MKGeneralException, match="not found"):
        PageRescheduleCheck().page(ctx)
