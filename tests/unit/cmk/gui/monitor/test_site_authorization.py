#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from http import HTTPStatus
from typing import Literal

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.livestatus_client import SiteConfigurations
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.fake_site import no_site_configuration
from tests.testlib.unit.gui.common_fixtures import create_aut_user_auth_wsgi_app
from tests.testlib.unit.gui.users import create_and_destroy_user
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK

pytestmark = pytest.mark.usefixtures("request_context")

_API = "/NO_SITE/check_mk/api/internal/monitor"
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


@pytest.fixture(name="wsgi_app_restricted_to_local_site")
def fixture_wsgi_app_restricted_to_local_site(
    wsgi_app: WebTestAppForCMK, load_config: Config, set_config: SetConfig
) -> Iterator[WebTestAppForCMK]:
    """Authenticated as a user authorized for NO_SITE only, with "remote" configured as well."""
    remote = no_site_configuration()
    remote["id"] = SiteId("remote")
    sites = SiteConfigurations(
        {SiteId("NO_SITE"): no_site_configuration(), SiteId("remote"): remote}
    )
    with (
        set_config(sites=sites),
        create_and_destroy_user(
            automation=True,
            custom_attrs={"authorized_sites": [SiteId("NO_SITE")]},
            config=load_config,
        ) as created,
    ):
        yield create_aut_user_auth_wsgi_app(wsgi_app, created)


def _rejection(app: WebTestAppForCMK, method: Literal["get", "post"], path: str, site: str) -> str:
    """The 400 response body, with the site name masked so responses for two sites compare."""
    if "{site}" in path:
        url, body = f"{_API}{path.format(site=site)}", {}
    else:
        url, body = (
            f"{_API}{path}",
            {"filter": {"type": "condition", "field": "site_id", "op": "one_of", "value": [site]}},
        )
    resp = app.call_method(
        method,
        url,
        params=json.dumps(body) if method == "post" else None,
        headers=_HEADERS,
        status=HTTPStatus.BAD_REQUEST,
    )
    return json.dumps(resp.json).replace(site, "<site>")


@pytest.mark.parametrize(
    "method, path",
    [
        pytest.param("post", "/hosts", id="hosts"),
        pytest.param("post", "/services", id="services"),
        pytest.param("get", "/hosts/heute?site_id={site}", id="host overview"),
        pytest.param("get", "/hosts/heute/action_menu?site_id={site}", id="host action menu"),
        pytest.param("get", "/hosts/heute/events?site_id={site}", id="host events"),
        pytest.param("post", "/hosts/heute/services?site_id={site}", id="host services"),
        pytest.param(
            "get", "/hosts/heute/service?site_id={site}&service_name=CPU", id="service overview"
        ),
        pytest.param(
            "get",
            "/hosts/heute/service/action_menu?site_id={site}&service_name=CPU",
            id="service action menu",
        ),
    ],
)
def test_a_site_outside_the_users_sites_is_rejected_like_one_that_does_not_exist(
    wsgi_app_restricted_to_local_site: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    method: Literal["get", "post"],
    path: str,
) -> None:
    with mock_livestatus(expect_status_query=False):
        unauthorized = _rejection(wsgi_app_restricted_to_local_site, method, path, "remote")
        unknown = _rejection(wsgi_app_restricted_to_local_site, method, path, "no-such-site")

    assert "Site '<site>' does not exist." in unknown
    assert unauthorized == unknown
