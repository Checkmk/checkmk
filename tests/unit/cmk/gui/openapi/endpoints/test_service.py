#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.unit.cmk.web_test_app import WebTestAppForCMK


@pytest.mark.usefixtures("with_admin_login")
def test_list_services_names_a_site_that_does_not_answer(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("services", [])
    mock_livestatus.make_site_unreachable("remote")
    mock_livestatus.expect_query(["GET services"], match_type="loose")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/1.0/domain-types/service/collections/all",
            params=json.dumps({"columns": ["host_name", "description"]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.OK,
        )

    assert resp.json["extensions"]["unreachable_sites"] == ["remote"]


@pytest.mark.usefixtures("with_admin_login")
def test_list_services_leaves_out_an_unreachable_site_it_was_not_asked_for(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("services", [])
    mock_livestatus.make_site_unreachable("remote")
    mock_livestatus.expect_query(["GET services"], match_type="loose", sites=["NO_SITE"])

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/1.0/domain-types/service/collections/all",
            params=json.dumps({"columns": ["host_name", "description"], "sites": ["NO_SITE"]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.OK,
        )

    assert resp.json["extensions"]["unreachable_sites"] == []
