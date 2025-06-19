#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Iterator

import pytest
from playwright.sync_api import BrowserContext, Page

from tests.gui_e2e.testlib.playwright.helpers import CmkCredentials
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard, ProblemDashboard
from tests.gui_e2e.testlib.playwright.pom.login import LoginPage
from tests.gui_e2e.testlib.playwright.pom.setup.edit_role import EditRole, RoleData
from tests.gui_e2e.testlib.playwright.pom.setup.roles_and_permissions import RolesAndPermissions
from tests.gui_e2e.testlib.playwright.pom.setup.user import AddUser, EditUser, UserData
from tests.gui_e2e.testlib.playwright.pom.setup.users import Users
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="new_role")
def create_new_role_by_cloning(
    dashboard_page: Dashboard,
    request: pytest.FixtureRequest,
    test_site: Site,
) -> Iterator[RoleData]:
    """Create a new role by cloning an existing role, delete it after the test.

    This fixture uses indirect pytest parametrization to define role details.

    Note: If this fixture is used together with the 'new_user' fixture, pay attention to the order
    of the fixtures in the test function signature. The 'new_role' fixture should be defined before
    the 'new_user' fixture.
    """
    role_data = request.param
    assert isinstance(role_data, RoleData), (
        f"Unexpected role data type: {type(role_data)}, expected type: RoleData"
    )
    cloned_role_id = role_data.copy_from_role_id + "x"
    roles_and_permissions_page = RolesAndPermissions(dashboard_page.page)
    logger.info(
        "Create new role '%s' by cloning '%s'", role_data.role_id, role_data.copy_from_role_id
    )
    roles_and_permissions_page.clone_role_button(role_data.copy_from_role_id).click()
    roles_and_permissions_page.role_properties_button(cloned_role_id).click()
    edit_role_page = EditRole(
        roles_and_permissions_page.page, cloned_role_id, navigate_to_page=False
    )
    edit_role_page.internal_id_text_field.fill(role_data.role_id)
    edit_role_page.alias_text_field.fill(role_data.alias)
    edit_role_page.save_button.click()
    yield role_data
    if os.getenv("CLEANUP", "1") == "1":
        roles_and_permissions_page.navigate()
        roles_and_permissions_page.delete_role(role_data.role_id, test_site.openapi.user_role)
        roles_and_permissions_page.activate_changes(test_site)


@pytest.fixture(name="new_user")
def create_new_user(
    dashboard_page: Dashboard,
    request: pytest.FixtureRequest,
    test_site: Site,
) -> Iterator[UserData]:
    """Create a new user and delete it after the test.

    This fixture uses indirect pytest parametrization to define user details.
    """
    user_data = request.param
    assert isinstance(user_data, UserData), (
        f"Unexpected user data type: {type(user_data)}, expected type: UserData"
    )
    add_user_page = AddUser(dashboard_page.page)
    logger.info("Create new user '%s'", user_data.user_id)
    add_user_page.fill_users_data(user_data)
    add_user_page.save_button.click()
    yield user_data
    if os.getenv("CLEANUP", "1") == "1":
        users_page = Users(dashboard_page.page)
        users_page.delete_user(user_data.user_id, test_site.openapi.users)
        users_page.activate_changes(test_site)


@pytest.mark.parametrize(
    "new_role, new_user",
    [
        pytest.param(
            RoleData(role_id="test_role", alias="Test role", copy_from_role_id="guest"),
            UserData(user_id="test_user", full_name="Test User", role="Test role"),
            id="delete_role_in_use",
        )
    ],
    indirect=True,
)
def test_delete_role_in_use(
    dashboard_page: Dashboard, new_role: RoleData, new_user: UserData
) -> None:
    """Test that a role in use cannot be deleted.

    Create a new role and a new user with this role. Check that the new role cannot be deleted.
    """
    role_data = new_role
    expected_error_msg = f"You cannot delete roles, that are still in use ({role_data.role_id})!"

    roles_and_permissions_page = RolesAndPermissions(dashboard_page.page)
    logger.info("Try to delete role '%s'", role_data.role_id)
    roles_and_permissions_page.delete_role_button(role_data.role_id).click()
    roles_and_permissions_page.delete_role_confirmation_button.click()
    roles_and_permissions_page.main_area.check_error(expected_error_msg)


@pytest.mark.parametrize(
    "new_user",
    [
        pytest.param(
            UserData(user_id="test_user", full_name="Test User", password="cmkcmkcmkcmk"),
            id="locked_user",
        )
    ],
    indirect=True,
)
def test_locked_user(
    dashboard_page: Dashboard,
    new_browser_context_and_page: tuple[BrowserContext, Page],
    new_user: UserData,
    test_site: Site,
) -> None:
    """Test locked user have no access to the site.

    Create a new user and lock it. Check that locked user is automatically logged out and cannot login.
    Then unlock the user and check that it can login again.
    """

    user_data = new_user
    new_user_credentials = CmkCredentials(user_data.user_id, user_data.password)  # type: ignore[arg-type]
    _, new_page = new_browser_context_and_page

    login_page = LoginPage(new_page, test_site.internal_url)
    logger.info("As '%s': login", user_data.user_id)
    login_page.login(new_user_credentials)
    problem_dashboard_page = ProblemDashboard(login_page.page, navigate_to_page=False)

    logger.info("As cmkadmin: lock the user '%s'", user_data.user_id)
    edit_user_page = EditUser(dashboard_page.page, user_data.user_id)
    edit_user_page.check_disable_login(True)
    edit_user_page.save_button.click()

    logger.info("As locked user '%s': reload the page and try to login", user_data.user_id)
    problem_dashboard_page.page.reload()
    login_page.validate_page()
    login_page.login(new_user_credentials)
    login_page.check_error("User is locked")

    logger.info("As cmkadmin: unlock the user '%s'", user_data.user_id)
    edit_user_page.navigate()
    edit_user_page.check_disable_login(False)
    edit_user_page.save_button.click()

    logger.info("As unlocked user '%s': login", user_data.user_id)
    login_page.login(new_user_credentials)
    problem_dashboard_page.validate_page()
