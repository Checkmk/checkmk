import logging
import re
from typing import NamedTuple
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.testlib.playwright.helpers import DropdownListNameToID
from tests.testlib.playwright.pom.page import CmkPage
from tests.testlib.playwright.pom.setup.users import Users

logger = logging.getLogger(__name__)


class UserData(NamedTuple):
    user_id: str
    full_name: str
    role: str


class AddUser(CmkPage):
    """Represent the 'Add user' page.

    To navigate: `Setup -> Users -> Add user`.
    """

    page_title = "Add user"

    def navigate(self) -> None:
        users_page = Users(self.page)
        users_page.add_user_button.click()
        self.page.wait_for_url(url=re.compile(quote_plus("mode=edit_user")), wait_until="load")
        self._validate_page()

    def _validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        self.main_area.check_page_title(self.page_title)
        expect(self.username_text_field).to_be_visible()
        expect(self.full_name_text_field).to_be_visible()

    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def save_button(self) -> Locator:
        return self.main_area.get_suggestion("Save")

    @property
    def username_text_field(self) -> Locator:
        return self.main_area.get_input("user_id")

    @property
    def full_name_text_field(self) -> Locator:
        return self.main_area.get_input("alias")

    def _role_checkbox(self, role_name: str) -> Locator:
        return (
            self.main_area.locator()
            .get_by_role("cell", name=role_name, exact=True)
            .locator("label")
        )

    def check_role(self, role_name: str, check: bool) -> None:
        if self._role_checkbox(role_name).is_checked() != check:
            self._role_checkbox(role_name).check()

    def fill_users_data(self, user_data: UserData) -> None:
        """Fill user data.

        Notes:
            - this method can be extended to fill more user data
            - role 'Normal monitoring user' is checked by default
        """
        logger.info("Fill user data for user '%s'", user_data.user_id)
        self.username_text_field.fill(user_data.user_id)
        self.full_name_text_field.fill(user_data.full_name)
        self.check_role(user_data.role, True)
