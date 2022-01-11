#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_wato_disabled_blocks_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    # add a host, so we can query it
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "neute", "folder": "/"}',
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
        ]
    )

    # calls to setup endpoints work correctly
    aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_config/neute",
        headers={"Accept": "application/json"},
        status=200,
    )

    # disable wato
    with aut_user_auth_wsgi_app.set_config(wato_enabled=False):
        # calls to setup endpoints are forbidden
        aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/objects/host_config/neute",
            headers={"Accept": "application/json"},
            status=403,
        )
        with live:
            # calls to monitoring endpoints should be allowed
            aut_user_auth_wsgi_app.call_method(
                "get",
                base + "/domain-types/service/collections/all",
                headers={"Accept": "application/json"},
                status=200,
            )
