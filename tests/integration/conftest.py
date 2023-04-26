#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os

import pytest

from tests.testlib.event_console import CMKEventConsole
from tests.testlib.openapi_session import RequestSessionRequestHandler
from tests.testlib.rest_api_client import ClientRegistry, get_client_registry, RestApiClient
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion
from tests.testlib.web_session import CMKWebSession


# Session fixtures must be in conftest.py to work properly
@pytest.fixture(scope="session", autouse=True, name="site")
def fixture_site() -> Site:
    if os.environ.get("RUNNING_IN_IDE") in ["yes", "1", "t", "true"]:
        # launch docker container
        # mount
        raise Exception

    logging.info("Setting up testsite")

    version = os.environ.get("VERSION", CMKVersion.DAILY)
    sf = get_site_factory(
        prefix="int_",
        update_from_git=version == "git",
        fallback_branch=current_base_branch_name,
    )

    site = sf.get_existing_site("test")

    if os.environ.get("REUSE"):
        logging.info("Reuse previously existing site in case it exists (REUSE=1)")
        if not site.exists():
            logging.info("Creating new site")
            site = sf.get_site("test")
        else:
            logging.info("Reuse existing site")
            site.set_livestatus_port_from_config()
            site.start()
    else:
        if site.exists():
            logging.info("Remove previously existing site (REUSE=0)")
            site.rm()

        logging.info("Creating new site")
        site = sf.get_site("test")

    logging.info("Site %s is ready!", site.id)

    return site


@pytest.fixture(scope="session", name="web")
def fixture_web(site: Site) -> CMKWebSession:
    web = CMKWebSession(site)
    web.login()
    site.enforce_non_localized_gui(web)
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


@pytest.fixture()
def clients(site: Site) -> ClientRegistry:
    rq = RequestSessionRequestHandler()
    rq.set_credentials("cmkadmin", site.admin_password)
    return get_client_registry(
        rq, f"{site.http_proto}://{site.http_address}:{site.apache_port}/{site.id}/check_mk/api/1.0"
    )


@pytest.fixture()
def skip_in_raw_edition(site: Site) -> None:
    if site.version.is_raw_edition():
        pytest.skip("Not relevant in raw edition")
