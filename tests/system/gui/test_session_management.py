#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import time
from collections.abc import Iterator

import pytest
from playwright.sync_api import BrowserContext, expect, Page

from tests.system.gui.testlib.playwright.helpers import CmkCredentials
from tests.system.gui.testlib.playwright.pom.login import LoginPage
from tests.system.gui.testlib.playwright.pom.setup.users import Users
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="short_session_timeouts")
def fixture_short_session_timeouts(test_site: Site) -> Iterator[None]:
    test_site.openapi.global_settings.update(
        "session_mgmt",
        {
            "max_duration": {
                "enforce_reauth": 80.0,
                "enforce_reauth_warning_threshold": 60.0,
            },
            "user_idle_timeout": 100.0,
        },
    )
    try:
        yield
    finally:
        test_site.openapi.global_settings.reset("session_mgmt")
        test_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@pytest.mark.usefixtures("short_session_timeouts")
def test_session_expiry_warning_and_logout(
    credentials: CmkCredentials,
    new_browser_context_and_page: tuple[BrowserContext, Page],
    test_site: Site,
) -> None:
    """
    Validate that with the session timeouts set to
        advise re-authentication after 60 sec,
        max duration 80 sec
        and user idle timeout 100 sec
    then
        after 60 seconds:
            session expiration warning is shown;
        after 80 seconds:
            session expires and user is redirected to login page.
    """

    _, page = new_browser_context_and_page
    login_page = LoginPage(page, test_site.internal_url)
    login_page.login(credentials)
    users_page = Users(page)

    logger.info("Waiting 60 seconds for session expiration warning...")
    time.sleep(62)
    users_page.page.reload()
    expect(
        users_page.session_warning_message,
        "Session expiration warning was not shown after 60 seconds",
    ).to_be_visible()

    logger.info("Waiting another 20 seconds for session to expire...")
    time.sleep(22)
    users_page.page.reload()
    login_page = LoginPage(users_page.page, navigate_to_page=False)
    try:
        login_page.validate_page()
        login_page.login(credentials)
    except AssertionError:
        pytest.fail("Login page was not shown after session expiry")
