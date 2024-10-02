import logging
from collections.abc import Iterator

import pytest

from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.setup.add_user import AddUser, UserData
from tests.testlib.playwright.pom.setup.edit_role import EditRole, RoleData
from tests.testlib.playwright.pom.setup.roles_and_permissions import RolesAndPermissions
from tests.testlib.playwright.pom.setup.users import Users

logger = logging.getLogger(__name__)


@pytest.fixture(name="new_role")
def create_new_role_by_cloning(
    dashboard_page: Dashboard, request: pytest.FixtureRequest
) -> Iterator[RoleData]:
    """Create a new role by cloning an existing role, delete it after the test.

    This fixture uses indirect pytest parametrization to define role details.

    Note: If this fixture is used together with the 'new_user' fixture, pay attention to the order
    of the fixtures in the test function signature. The 'new_role' fixture should be defined before
    the 'new_user' fixture.
    """
    role_data = request.param
    assert isinstance(
        role_data, RoleData
    ), f"Unexpected role data type: {type(role_data)}, expected type: RoleData"
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
    roles_and_permissions_page.navigate()
    roles_and_permissions_page.delete_role(role_data.role_id)
    roles_and_permissions_page.activate_changes()


@pytest.fixture(name="new_user")
def create_new_user(
    dashboard_page: Dashboard, request: pytest.FixtureRequest
) -> Iterator[UserData]:
    """Create a new user and delete it after the test.

    This fixture uses indirect pytest parametrization to define user details.
    """
    user_data = request.param
    assert isinstance(
        user_data, UserData
    ), f"Unexpected user data type: {type(user_data)}, expected type: UserData"
    add_user_page = AddUser(dashboard_page.page)
    logger.info("Create new user '%s'", user_data.user_id)
    add_user_page.fill_users_data(user_data)
    add_user_page.save_button.click()
    yield user_data
    users_page = Users(dashboard_page.page)
    users_page.delete_user(user_data.user_id)
    users_page.activate_changes()


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
