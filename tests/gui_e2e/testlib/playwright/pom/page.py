#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from abc import abstractmethod
from re import Pattern
from typing import Literal, overload
from urllib.parse import urljoin

from playwright.sync_api import expect, FrameLocator, Locator, Page, Response

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID, Keys, LocatorHelper
from tests.gui_e2e.testlib.playwright.timeouts import TIMEOUT_ASSERTIONS

logger = logging.getLogger(__name__)


class CmkPage(LocatorHelper):
    """Parent object representing a Checkmk GUI page."""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
        contain_filter_sidebar: bool = False,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(page, timeout_assertions, timeout_navigation)
        self._navigate_to_page = navigate_to_page
        self.main_menu = MainMenu(self.page)
        self.main_area = MainArea(self.page, self._dropdown_list_name_to_id())
        self.sidebar = Sidebar(self.page)
        if contain_filter_sidebar:
            self.filter_sidebar = FilterSidebar(self.page)
        if self._navigate_to_page:
            self.navigate()
        else:
            self._validate_page()
        self._url = self.page.url

    @abstractmethod
    def navigate(self) -> None:
        """Navigate to the page.

        Perform navigation steps, wait for the page to load and validate
        the correct page is displayed by using the `_validate_page` method.
        """

    @abstractmethod
    def _validate_page(self) -> None:
        """Validate correct page is displayed.

        Ensure the expected page is displayed by checking the page title,
        url or other elements that are unique to the page.
        """

    @abstractmethod
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        """Provide mapping between `dropdown list` names and corresponding `menu ID`s.

        In addition to the `quick suggestion` buttons present on a page,
        `dropdown list`s provide additional options to a user, in form of an item list.
        Item list corresponds to a web element in the UI, consisting of a `menu ID`.
        Using `menu ID` ensures that an instruction is executed from the desired `dropdown list`.
        """

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator(selector)

    def activate_selected(self) -> None:
        logger.info("Click 'Activate on selected sites' button")
        self.main_area.locator("#menu_suggestion_activate_selected").click()

    def expect_success_state(self) -> None:
        logger.info("Check changes were activated successfully")
        expect(
            self.main_area.locator("#site_gui_e2e_central_status.msg.state_success")
        ).to_be_visible()

        expect(
            self.main_area.locator("#site_gui_e2e_central_progress.progress.state_success")
        ).to_be_visible()

        # assert no further changes are pending
        expect(self.main_area.locator("div.page_state.no_changes")).to_be_visible()

    def goto_main_dashboard(self) -> None:
        """Click the banner and wait for the dashboard"""
        logger.info("Navigate to 'Main dashboard' page")
        self.main_menu.main_page.click()
        self.main_area.check_page_title("Main dashboard")

    def select_host(self, host_name: str) -> None:
        logger.info("Click on host link: %s", host_name)
        self.main_area.locator(f"td a:has-text('{host_name}')").click()

    def goto_add_sidebar_element(self) -> None:
        logger.info("Navigate to 'Add sidebar element' page")
        self.locator("div#check_mk_sidebar >> div#add_snapin > a").click()
        self.main_area.check_page_title("Add sidebar element")

    def press_keyboard(self, key: Keys) -> None:
        logger.info("Press keyboard key: %s", key.value)
        self.page.keyboard.press(str(key.value))

    def get_link(self, name: str | Pattern[str], exact: bool = True) -> Locator:
        """Returns a web-element from the `main_area`, which is a `link`."""
        return self.main_area.locator().get_by_role(role="link", name=name, exact=exact)

    def activate_changes(self) -> None:
        logger.info("Activate changes")
        self.get_link(re.compile("^[1-9][0-9]* changes?$"), exact=False).click()
        self.activate_selected()
        self.expect_success_state()

    def goto(self, url: str, event: str = "load") -> None:
        """Override `Page.goto`. Additionally, wait for the page to `load`, by default.

        The `event` to be expected can be changed.
        """
        with self.page.expect_event(event) as _:
            self.page.goto(url)

    def check_no_errors(self, timeout: float = TIMEOUT_ASSERTIONS / 4) -> None:
        """Check that no errors are present on the page."""
        expect(self.locator("div.error"), "Some errors are present on the page").not_to_be_visible(
            timeout=timeout
        )

    def go(
        self,
        url: str,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] | None = None,
        referer: str | None = None,
    ) -> Response | None:
        """Navigate using URLs relative to current page.

        Note: `urljoin` is used to combine`url`s. Example,
        joining `http://localhost/index.py` and `werk.py` results in `http://localhost/werk.py`.
        """
        return self.page.goto(urljoin(self._url, url), wait_until=wait_until, referer=referer)


class MainMenu(LocatorHelper):
    """functionality to find items from the main menu"""

    @overload
    def locator(self, selector: None = None) -> Locator: ...

    @overload
    def locator(self, selector: str) -> Locator: ...

    def locator(self, selector: str | None = None) -> Locator:
        _loc = self.page.locator("#check_mk_navigation")
        if selector:
            _loc = _loc.locator(selector)
        self._unique_web_element(_loc)
        return _loc

    def _sub_menu(
        self,
        menu: str,
        sub_menu: str | None,
        show_more: bool = False,
        exact: bool = True,
    ) -> Locator:
        """Main menu -> Open `menu` -> Show more (optional) -> `sub menu`

        Return `locator` of `menu`, if `sub_menu` is `None`.
        """
        _loc = self.locator().get_by_role(role="link", name=menu)
        if sub_menu:
            _loc.click()
            if show_more:
                self.page.get_by_role(role="link", name="show more", exact=True)
            _loc = self.page.get_by_role(role="link", name=sub_menu, exact=exact)
        self._unique_web_element(_loc)
        return _loc

    @property
    def main_page(self) -> Locator:
        return self._sub_menu("Go to main page", sub_menu=None)

    def monitor_menu(
        self, sub_menu: str | None = None, show_more: bool = False, exact: bool = False
    ) -> Locator:
        """main menu -> Open monitor -> show more(optional) -> sub menu"""
        return self._sub_menu("Monitor", sub_menu, show_more, exact)

    def setup_menu(
        self, sub_menu: str | None = None, show_more: bool = False, exact: bool = False
    ) -> Locator:
        """main menu -> Open setup -> show more(optional) -> sub menu"""
        return self._sub_menu("Setup", sub_menu, show_more, exact)

    def user_menu(self, sub_menu: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open user -> show more(optional) -> sub menu"""
        return self._sub_menu("User", sub_menu, show_more=False, exact=exact)

    def help_menu(self, sub_menu: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open help -> show more(optional) -> sub menu"""
        return self._sub_menu("Help", sub_menu, show_more=False, exact=exact)

    def _searchbar(self, menu: Literal["Setup", "Monitor"], searchbar_name: str) -> Locator:
        self._sub_menu(menu, sub_menu=None).click()
        _location = self.locator().get_by_role(role="textbox", name=searchbar_name)
        self._unique_web_element(_location)
        return _location

    @property
    def monitor_searchbar(self) -> Locator:
        """Main menu -> Open monitor -> searchbar"""
        return self._searchbar(menu="Monitor", searchbar_name="Search with regular expressions")

    @property
    def monitor_all_hosts(self) -> Locator:
        """main menu -> monitoring -> All hosts"""
        return self.monitor_menu("All hosts")

    @property
    def setup_searchbar(self) -> Locator:
        """Main menu -> Open setup -> searchbar"""
        return self._searchbar(
            menu="Setup", searchbar_name="Search for menu entries, settings, hosts and rulesets"
        )

    @property
    def setup_hosts(self) -> Locator:
        return self.setup_menu("Hosts")

    @property
    def user_color_theme(self) -> Locator:
        """Main menu -> Open user -> Color theme"""
        return self.user_menu("Color theme", exact=False)

    @property
    def user_color_theme_button(self) -> Locator:
        """Main menu -> Open user -> Color theme button"""
        self.user_menu().click()
        return self.locator("#ui_theme")

    @property
    def user_sidebar_position(self) -> Locator:
        return self.user_menu("Sidebar position", exact=False)

    @property
    def user_sidebar_position_button(self) -> Locator:
        """Main menu -> Open user -> Sidebar position"""
        self.user_menu().click()
        return self.locator("#sidebar_position")

    @property
    def user_edit_profile(self) -> Locator:
        return self.user_menu("Edit profile")

    @property
    def user_notification_rules(self) -> Locator:
        return self.user_menu("Notification rules")

    @property
    def user_change_password(self) -> Locator:
        return self.user_menu("Change password")

    @property
    def user_two_factor_authentication(self) -> Locator:
        return self.user_menu("Two-factor authentication")

    @property
    def user_logout(self) -> Locator:
        return self.user_menu("Logout")

    @property
    def help_beginners_guide(self) -> Locator:
        return self.help_menu("Beginner's guide")

    @property
    def help_user_manual(self) -> Locator:  #
        return self.help_menu("User manual")

    @property
    def help_video_tutorials(self) -> Locator:
        return self.help_menu("Video tutorials")

    @property
    def help_community_forum(self) -> Locator:
        return self.help_menu("Community forum")

    @property
    def help_plugin_api_intro(self) -> Locator:
        return self.help_menu("Check plug-in API introduction")

    @property
    def help_plugin_api_docs(self) -> Locator:
        return self.help_menu("Plug-in API references")

    @property
    def help_rest_api_intro(self) -> Locator:
        return self.help_menu("REST API introduction")

    @property
    def help_rest_api_docs(self) -> Locator:
        return self.help_menu("REST API documentation")

    @property
    def help_rest_api_gui(self) -> Locator:
        return self.help_menu("REST API interactive GUI")

    @property
    def help_info(self) -> Locator:
        return self.help_menu("Info")

    @property
    def help_saas_status_page(self) -> Locator:
        return self.help_menu("Status page")

    @property
    def help_suggest_product_improvement(self) -> Locator:
        return self.help_menu("Suggest a product improvement")

    @property
    def help_werks(self) -> Locator:
        return self.help_menu("Change log (Werks)")

    def logout(self) -> None:
        logger.info("Click logout button")
        self.user_logout.click()
        self.page.wait_for_url(url=re.compile("login.py$"), wait_until="load")


class MainArea(LocatorHelper):
    """functionality to find items from the main area"""

    def __init__(
        self,
        page: Page,
        dropdown_list_name_to_id: DropdownListNameToID,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(page, timeout_assertions, timeout_navigation)
        self._dropdown_list_name_to_id = dropdown_list_name_to_id

    @overload
    def locator(self, selector: None = None) -> FrameLocator: ...

    @overload
    def locator(self, selector: str) -> Locator: ...

    def locator(self, selector: str | None = None) -> Locator | FrameLocator:
        _loc = self.page.frame_locator("iframe[name='main']")
        if selector is None:
            return _loc
        return _loc.locator(selector)

    def check_page_title(self, title: str | Pattern[str]) -> None:
        """check the page title"""
        expect(self.locator(".titlebar a>>nth=0")).to_have_text(title)

    def expect_no_entries(self) -> None:
        """Expect no previous entries are found in the page.

        If it fails, the current test site should be cleaned up.
        """
        expect(self.get_text("No entries.")).to_be_visible()

    def locator_via_xpath(self, element: str, text: str) -> Locator:
        """Return a locator defined by element and text via xpath."""
        return self.locator(f"//{element}[text() = '{text}']")

    @property
    def page_menu_bar(self) -> Locator:
        return self.locator("table#page_menu_bar")

    def dropdown_button(self, name: str, exact: bool = True) -> Locator:
        return self.page_menu_bar.get_by_role(role="heading", name=name, exact=exact)

    def dropdown_list(self, dropdown_button: str) -> Locator:
        try:
            menu_id = getattr(self._dropdown_list_name_to_id, dropdown_button)
        except AttributeError as e:
            e.add_note(
                f"No `menu ID` found corresponding to dropdown list: '{dropdown_button}'!\n"
                "`MainArea` is initialized with incomplete mapping of `dropdown_list_name_to_id`."
            )
            raise e
        return self.locator(f"div#{menu_id}")

    def item_in_dropdown_list(self, dropdown_button: str, item: str) -> Locator:
        return self.dropdown_list(dropdown_button).locator(f"span:has-text('{item}')")

    def click_item_in_dropdown_list(self, dropdown_button: str, item: str) -> None:
        self.dropdown_button(dropdown_button).click()
        expect(self.dropdown_list(dropdown_button)).to_be_visible()
        self.item_in_dropdown_list(dropdown_button, item).click()


class Sidebar(LocatorHelper):
    """functionality to find items from the sidebar"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator("#check_mk_sidebar").locator(selector)


class FilterSidebar(LocatorHelper):
    """functionality to find items from the filter sidebar"""

    @overload
    def locator(self, selector: None = None) -> Locator: ...

    @overload
    def locator(self, selector: str) -> Locator: ...

    def locator(self, selector: str | None = None) -> Locator:
        _loc = self.page.frame_locator("iframe[name='main']").locator("div#popup_filters")
        if selector:
            _loc = _loc.locator(selector)
        self._unique_web_element(_loc)
        return _loc

    @property
    def apply_filters_button(self) -> Locator:
        return self.locator().get_by_role("button", name="Apply filters")

    @property
    def add_filter_button(self) -> Locator:
        return self.locator().get_by_role("link", name="Add filter")

    @property
    def filters_list(self) -> Locator:
        return self.locator("div#_popup_filter_list")

    def filter_button(self, filter_name: str) -> Locator:
        return self.filters_list.get_by_role("link", name=filter_name)

    @property
    def select_service_field(self) -> Locator:
        return self.locator("#select2-service_regex-container")

    @property
    def search_text_field(self) -> Locator:
        return self.page.frame_locator("iframe[name='main']").get_by_role("searchbox")

    @property
    def select_host_field(self) -> Locator:
        return self.locator("#select2-host_regex-container")

    @property
    def last_service_state_change_filter(self) -> Locator:
        return self.locator("span:text-is('Last service state change')")

    @property
    def last_service_state_change_from_text_field(self) -> Locator:
        return self.locator("input[name='svc_last_state_change_from']")

    @property
    def last_service_state_change_from_dropdown(self) -> Locator:
        return self.locator("#select2-svc_last_state_change_from_range-container")

    @property
    def last_service_state_change_until_text_field(self) -> Locator:
        return self.locator("input[name='svc_last_state_change_until']")

    @property
    def last_service_state_change_until_dropdown(self) -> Locator:
        return self.locator("#select2-svc_last_state_change_until_range-container")

    def dropdown_option(self, option_name: str, exact: bool = False) -> Locator:
        return self.page.frame_locator("iframe[name='main']").get_by_role(
            "option", name=option_name, exact=exact
        )

    def apply_last_service_state_change_filter(
        self, from_units: str, from_value: str, until_units: str, until_value: str
    ) -> None:
        try:
            expect(self.last_service_state_change_filter).to_be_visible(timeout=3000)
        except AssertionError:
            self.add_filter_button.click()
            self.filter_button("Last service state change").click()

        self.last_service_state_change_from_dropdown.click()
        self.dropdown_option(from_units).click()
        self.last_service_state_change_from_text_field.fill(from_value)

        self.last_service_state_change_until_dropdown.click()
        self.dropdown_option(until_units).click()
        self.last_service_state_change_until_text_field.fill(until_value)

    def apply_service_filter(self, service_filter: str) -> None:
        self.select_service_field.click()
        self.search_text_field.fill(service_filter)
        self.dropdown_option(service_filter, exact=True).click()

    def apply_host_filter(self, host_filter: str) -> None:
        self.select_host_field.click()
        self.search_text_field.fill(host_filter)
        # TODO: remove 'nth(0)' after fixing CMK-19975
        self.dropdown_option(host_filter, exact=True).nth(0).click()

    def apply_filters(self, expected_locator: Locator) -> None:
        self.apply_filters_button.click()
        self.page.wait_for_load_state("load")
        expect(expected_locator).to_be_visible()
