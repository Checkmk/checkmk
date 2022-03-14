#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_hosts_generic_filter(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus,
):
    live: MockLiveStatusConnection = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"

    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
            },
        ],
    )

    live.expect_query(
        [
            "GET hosts",
            "Columns: name",
        ],
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/host/collections/all",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1

    live.expect_query(
        [
            "GET hosts",
            "Columns: name alias",
            "Filter: alias ~ heute",
        ],
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base
            + '/domain-types/host/collections/all?query={"op": "~", "left": "alias", "right": "heute"}&columns=name&columns=alias',
            headers={"Accept": "application/json"},
            status=200,
        )
        assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_livestatus_hosts_empty_query(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus,
):

    live = mock_livestatus

    base = "/NO_SITE/check_mk/api/1.0"
    live.add_table(
        "hosts",
        [
            {
                "name": "heute",
                "address": "127.0.0.1",
                "alias": "heute",
                "downtimes_with_info": [],
                "scheduled_downtime_depth": 0,
            },
        ],
    )
    live.expect_query(
        [
            "GET hosts",
            "Columns: name alias",
        ],
    )
    with live:
        resp = aut_user_auth_wsgi_app.call_method(
            "get",
            base + "/domain-types/host/collections/all?query={}&columns=name&columns=alias",
            headers={"Accept": "application/json"},
            status=200,
        )
        assert resp.json["value"][0]["id"] == "heute"
