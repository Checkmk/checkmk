#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import time

import pytest
from playwright.sync_api import BrowserContext, expect, Page

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.gui_e2e.testlib.playwright.pom.monitor.hosts_dashboard import LinuxHostsDashboard
from tests.gui_e2e.testlib.playwright.pom.setup.session_management import (
    SessionManagementPage,
    TimeoutValues,
)
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


def test_session_expiry_warning_and_logout(
    credentials: CmkCredentials,
    new_browser_context_and_page: tuple[BrowserContext, Page],
    test_site: Site,
) -> None:
    """
    Validate that if session timeouts are set as follows:
        advise re-authentication to 1 min
        and max duration to 2 min
        user idle timeout to 3 min
    then
        after 1 minute:
            session expiration warning is shown;
        after 2 minutes:
            session expires and user is redirected to login page.
    """

    _, page = new_browser_context_and_page
    login_page = LoginPage(page, test_site.internal_url)
    login_page.login(credentials)
    linux_hosts_dashboard = LinuxHostsDashboard(page)

    try:
        session_page = SessionManagementPage(linux_hosts_dashboard.page)

        logger.info(
            "Setting session timeouts:"
            "\n\tmax duration 2 min, advise re-authentication 1 min, idle timeout 3 min"
        )
        session_page.set_max_duration_values(TimeoutValues(days=0, hours=0, minutes=2))
        session_page.set_advise_reauth_values(TimeoutValues(days=0, hours=0, minutes=1))
        session_page.set_idle_timeout_values(TimeoutValues(days=0, hours=0, minutes=3))
        session_page.save_options()
        session_page.navigate()
        assert session_page.get_max_duration_values() == TimeoutValues(days=0, hours=0, minutes=2)
        assert session_page.get_advise_reauth_values() == TimeoutValues(days=0, hours=0, minutes=1)
        assert session_page.get_idle_timeout_values() == TimeoutValues(days=0, hours=0, minutes=3)

        logger.info("Waiting 1 minute for session expiration warning...")
        time.sleep(62)
        session_page.page.reload()
        expect(
            session_page.session_warning_message,
            "Session expiration warning was not shown after 1 minute",
        ).to_be_visible(timeout=5_000)

        logger.info("Waiting another minute for session to expire...")
        time.sleep(62)
        linux_hosts_dashboard.page.reload()
        login_page = LoginPage(linux_hosts_dashboard.page, navigate_to_page=False)
        try:
            login_page.validate_page()
            login_page.login(credentials)
        except AssertionError:
            pytest.fail("Login page was not shown after session expiry")
    finally:
        session_page = SessionManagementPage(linux_hosts_dashboard.page)
        session_page.reset_to_default()
