#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urljoin

import pytest
from playwright.sync_api import BrowserContext, expect, Page

from tests.gui_e2e.testlib.open_ldap import Group, OpenLDAPManager, User
from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.testlib.site import Site
from tests.testlib.utils import is_containerized


@pytest.fixture(name="tmp_path_module", scope="module")
def get_tmp_path_module(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("test_open_ldap")


@pytest.fixture(name="open_ldap_manager", scope="module")
def create_open_ldap_manager(tmp_path_module: Path) -> Iterator[OpenLDAPManager]:
    """Create OpenLDAPManager instance.

    OpenLDAPManager handles setting up and tearing down local LDAP server. It creates
    specified groups and users in the LDAP server.
    """
    groups = [Group("developers"), Group("customers")]
    users = [
        User("james.brown", "developers", "James Brown", "Brown", "password123"),
        User("jane.doe", "customers", "Jane Doe", "Doe", "password123"),
    ]
    with OpenLDAPManager(groups, users, tmp_path_module) as open_ldap_manager:
        yield open_ldap_manager


@pytest.fixture(name="ldap_connection", scope="module")
def create_ldap_connection(open_ldap_manager: OpenLDAPManager, test_site: Site) -> Iterator:
    """Create an LDAP connection in CheckMK site via REST API.

    Add an LDAP connection for local OpenLDAP server. Filter users by 'developers' group.
    Delete the LDAP connection after the test.
    """
    ldap_id = "test_ldap"
    test_site.openapi.ldap_connection.create(
        ldap_id,
        user_base_dn="ou=developers,dc=ldap,dc=local",
        user_search_filter="(objectclass=inetOrgPerson)",
        user_id_attribute="uid",
        group_base_dn="ou=developers,dc=ldap,dc=local",
        group_search_filter="(objectclass=organizationalUnit)",
        ldap_server="localhost",
        bind_dn="cn=admin,dc=ldap,dc=local",
        password=open_ldap_manager.admin_password,
    )
    yield
    test_site.openapi.ldap_connection.delete(ldap_id)


@pytest.fixture(name="valid_ldap_credentials", scope="module")
def get_valid_ldap_credentials(open_ldap_manager: OpenLDAPManager) -> CmkCredentials:
    """Return LDAP user credentials from 'developers' group"""
    for user in open_ldap_manager.users:
        if user.ou == "developers":
            username, password = user.uid, user.password
            return CmkCredentials(username, password)
    raise ValueError("No user with 'developers' group found")


@pytest.fixture(name="invalid_ldap_credentials", scope="module")
def get_invalid_ldap_credentials(open_ldap_manager: OpenLDAPManager) -> CmkCredentials:
    """Return LDAP user credentials from 'customers' group"""
    for user in open_ldap_manager.users:
        if user.ou == "customers":
            username, password = user.uid, user.password
            return CmkCredentials(username, password)
    raise ValueError("No user with 'customers' group found")


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(
            r"index.py?start_url=%2F<SITE_ID>%2Fcheck_mk%2Fbookmark_lists.py", id="browser"
        ),
        pytest.param(r"mobile_view.py?view_name=mobile_notifications", id="mobile"),
    ],
)
def test_redirected_to_desired_page(
    new_browser_context_and_page: tuple[BrowserContext, Page],
    credentials: CmkCredentials,
    test_site: Site,
    url: str,
) -> None:
    _, page = new_browser_context_and_page
    cmk_page = url.replace(r"<SITE_ID>", test_site.id)
    visit_url = urljoin(test_site.internal_url, cmk_page)

    login_page = LoginPage(page, visit_url)
    login_page.login(credentials)
    expect(login_page.page).to_have_url(re.compile(f"{re.escape(cmk_page)}$"))


@pytest.mark.skipif(not is_containerized(), reason="Only to be run in a container")
def test_ldap_user_login_success(
    new_browser_context_and_page: tuple[BrowserContext, Page],
    test_site: Site,
    valid_ldap_credentials: CmkCredentials,
    ldap_connection: None,
) -> None:
    """Test login with valid LDAP user credentials.

    Test that user with LDAP credentials from correct group ('developers') can login
    to the Checkmk site.
    """
    _, page = new_browser_context_and_page
    login_page = LoginPage(page, test_site.internal_url)
    login_page.login(valid_ldap_credentials)
    login_page.main_menu.monitor_menu("Problem dashboard").click()
    login_page.main_area.check_page_title("Problem dashboard")


@pytest.mark.skipif(not is_containerized(), reason="Only to be run in a container")
def test_ldap_user_login_failed(
    new_browser_context_and_page: tuple[BrowserContext, Page],
    test_site: Site,
    invalid_ldap_credentials: CmkCredentials,
    ldap_connection: None,
) -> None:
    """Test login with invalid LDAP user credentials.

    The test check that user with LDAP credentials from incorrect group ('customers')
    cannot login to the Checkmk site.
    """
    _, page = new_browser_context_and_page
    login_page = LoginPage(page, test_site.internal_url)
    login_page.login(invalid_ldap_credentials)
    login_page.check_error("Incorrect username or password. Please try again.")
