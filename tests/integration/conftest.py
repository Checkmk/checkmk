#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.event_console import CMKEventConsole
from tests.testlib.openapi_session import RequestSessionRequestHandler
from tests.testlib.rest_api_client import RestApiClient
from tests.testlib.site import get_site_factory, Site
from tests.testlib.web_session import CMKWebSession


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True, name="site")
def fixture_site() -> Site:
    sf = get_site_factory(prefix="int_", update_from_git=True, install_test_python_modules=True)
    return sf.get_existing_site("test")


@pytest.fixture(scope="session", name="web")
def fixture_web(site: Site) -> CMKWebSession:
    web = CMKWebSession(site)
    web.login()
    web.enforce_non_localized_gui()
    return web


@pytest.fixture(scope="session")
def ec(site: Site) -> CMKEventConsole:
    return CMKEventConsole(site)


@pytest.fixture()
def rest_api_client(site: Site) -> RestApiClient:
    rq = RequestSessionRequestHandler()
    rq.set_credentials("cmkadmin", site.admin_password)
    return RestApiClient(
        rq, f"{site.http_proto}://{site.http_address}:{site.apache_port}/{site.id}/check_mk/api/1.0"
    )
