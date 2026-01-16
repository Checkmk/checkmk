#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from abc import abstractmethod
from re import Pattern
from typing import Literal, override
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import expect, Locator, Page, Response

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID, Keys, LocatorHelper
from tests.gui_e2e.testlib.playwright.timeouts import TIMEOUT_ACTIVATE_CHANGES_MS
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


class CmkPage(LocatorHelper):
    """Parent object representing a Checkmk GUI page."""

    def __init__(
        self, page: Page, navigate_to_page: bool = True, contain_filter_sidebar: bool = False
    ) -> None:
        super().__init__(page)
        self._navigate_to_page = navigate_to_page
        self.main_menu = MainMenu(self.page)
        self.main_area = MainArea(self.page, self._dropdown_list_name_to_id())
        self.sidebar = Sidebar(self.page)
        if contain_filter_sidebar:
            self.filter_sidebar = FilterSidebar(self.page)
        if self._navigate_to_page:
            self.navigate()
        else:
            self.validate_page()
        self._url = self.page.url

    @abstractmethod
    def navigate(self) -> None:
        """Navigate to the page.

        Perform navigation steps, wait for the page to load and validate
        the correct page is displayed by using the `validate_page` method.
        """

    @abstractmethod
    def validate_page(self) -> None:
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

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        if not selector:
            selector = "xpath=."
        _loc = self.page.locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        return _loc

    @property
    def session_warning_message(self) -> Locator:
        """Warning message for maximum session duration almost reached."""
        return self.main_area.locator(
            "div.warning.flashed", has_text="Maximum session duration almost reached"
        )

    def _activate_selected(self) -> None:
        logger.info("Click 'Activate on selected sites' button")
        self.main_area.locator("#menu_suggestion_activate_selected").click()

    def _expect_success_state(self) -> None:
        logger.info("Check changes were activated successfully")

        progress_elements = self.main_area.locator("td.repprogress > div.progress")
        success_elements = self.main_area.locator("td.repprogress > div.progress.state_success")

        expect(
            success_elements, message="Changes were not successfully activated in all the sites"
        ).to_have_count(progress_elements.count())

        # TODO: implement the check for 'no changes' state in the new menu budget
        # It seems to be not trustworthy by now, so we disable it for now.
        # expect(self.main_area.locator("div.page_state.no_changes")).to_be_visible()

    def select_host(self, host_name: str) -> None:
        logger.info("Click on host link: %s", host_name)
        self.main_area.locator(f"td a:has-text('{host_name}')").click()

    def press_keyboard(self, key: Keys) -> None:
        logger.info("Press keyboard key: %s", key.value)
        self.page.keyboard.press(str(key.value))

    def get_link(self, name: str | Pattern[str], exact: bool = True) -> Locator:
        """Returns a web-element from the `main_area`, which is a `link`."""
        return self.main_area.locator().get_by_role(role="link", name=name, exact=exact)

    def activate_changes(self, site: Site | None = None, navigate_to_page: bool = True) -> None:
        """Activate changes using the UI.

        Args:
            site (Site | None, optional): Fail safe mechanism.
                In case an error arises, UI related or otherwise,
                make sure to activate the changes using REST-API.
                Defaults to None.
                NOTE: Activate 'foreign changes' is enabled using REST-API!
        """
        logger.info("Activate changes")
        try:
            if navigate_to_page:
                self.main_menu.changes_menu("Open full view").click()
            self.page.wait_for_url(url=re.compile(quote_plus("wato.py?mode=changelog")))
            self._activate_selected()
            self._expect_success_state()
        except Exception as e:
            if site:
                logger.warning("fail-safe: could not activate changes using UI; using REST-API...")
                site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
            else:
                raise e

    def goto(self, url: str, event: str = "load") -> None:
        """Override `Page.goto`. Additionally, wait for the page to `load`, by default.

        The `event` to be expected can be changed.
        """
        with self.page.expect_event(event) as _:
            self.page.goto(url)

    def check_no_errors(self, timeout: float = TIMEOUT_ACTIVATE_CHANGES_MS / 4) -> None:
        """Check that no errors are present on the page."""
        expect(
            self.main_area.locator("div.error"), message="Some errors are present on the page!"
        ).not_to_be_visible(timeout=timeout)

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
    """Functionality to find items from the main menu"""

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        _loc = self.page.locator("#check_mk_navigation")
        if selector:
            _loc = _loc.locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
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
            _popup_menu = self.page.locator("div.popup_trigger.active").locator("div.popup_menu")
            _loc = _popup_menu.get_by_role(role="link", name=sub_menu, exact=exact)
        self._unique_web_element(_loc)
        return _loc

    @property
    def main_page(self) -> Locator:
        return self._sub_menu("Go to main page", sub_menu=None)

    def search_menu(self) -> Locator:
        """main menu -> Open search -> focus on search input"""
        return self._sub_menu("Search", None)

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

    def changes_menu(self, button: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open changes -> activate changes app"""
        _loc = self._sub_menu("Changes", None, False, False)
        if button:
            _loc.click()
            _loc = self.page.get_by_role(role="button", name=button, exact=exact)
        self._unique_web_element(_loc)
        return _loc

    def customize_menu(self, sub_menu: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open customize -> show more(optional) -> sub menu"""
        return self._sub_menu("Customize", sub_menu, False, exact)

    def user_menu(self, sub_menu: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open user -> show more(optional) -> sub menu"""
        return self._sub_menu("User", sub_menu, show_more=False, exact=exact)

    def help_menu(self, sub_menu: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open help -> show more(optional) -> sub menu"""
        return self._sub_menu("Help", sub_menu, show_more=False, exact=exact)

    def rest_api_help_menu(self, sub_menu: str | None = None, exact: bool = False) -> Locator:
        """main menu -> Open help -> REST API -> sub menu"""
        rest_api_text = "REST API"
        self.help_menu(rest_api_text)
        return self._sub_menu(rest_api_text, sub_menu, show_more=False, exact=exact)

    @property
    def active_side_menu_popup(self) -> Locator:
        """Return the locator of the currently active side menu popup.

        As only one side menu can be interacted with at a time.
        """
        loc = self.page.locator("div.popup_trigger.active").locator("div.popup_menu_handler")
        expect(loc, message="None of the side menu popups are open!").to_have_count(1)
        return loc

    @property
    def global_searchbar(self) -> Locator:
        self._sub_menu("Search", sub_menu=None).click()
        self._unique_web_element(
            _location := self.active_side_menu_popup.get_by_placeholder("Search")
        )
        return _location

    @property
    def monitor_all_hosts(self) -> Locator:
        """main menu -> monitoring -> All hosts"""
        return self.monitor_menu("All hosts")

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
    def help_user_guide(self) -> Locator:
        return self.help_menu("User Guide")

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
        return self.rest_api_help_menu("Introduction")

    @property
    def help_rest_api_docs(self) -> Locator:
        return self.rest_api_help_menu("Documentation")

    @property
    def help_rest_api_gui(self) -> Locator:
        return self.rest_api_help_menu("Interactive GUI")

    @property
    def help_saas_status_page(self) -> Locator:
        return self.help_menu("Status page")

    @property
    def help_suggest_product_improvement(self) -> Locator:
        return self.help_menu("Suggest a product improvement")

    @property
    def help_werks(self) -> Locator:
        return self.help_menu("Change log (Werks)")

    @property
    def changes_activate_pending_btn(self) -> Locator:
        return self.changes_menu("Activate pending changes", exact=True)

    @property
    def changes_open_full_view_btn(self) -> Locator:
        return self.changes_menu("Open full view", exact=True)

    def logout(self) -> None:
        logger.info("Click logout button")
        self.user_logout.click()
        self.page.wait_for_url(url=re.compile("login.py$"), wait_until="load")


class MainArea(LocatorHelper):
    """Functionality to find items from the main area"""

    def __init__(
        self,
        page: Page,
        dropdown_list_name_to_id: DropdownListNameToID,
    ) -> None:
        super().__init__(page)
        self._dropdown_list_name_to_id = dropdown_list_name_to_id

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        if not selector:
            selector = ":scope"
        _loc = self._iframe_locator.locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        return _loc

    @property
    def page_title_locator(self) -> Locator:
        """Return the page title locator."""
        return self.locator(".titlebar a.title")

    def check_page_title(self, title: str | Pattern[str]) -> None:
        """check the page title"""
        expect(self.page_title_locator).to_have_text(title)

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

    @property
    def page_menu_popups(self) -> Locator:
        return self.locator("div#page_menu_popups")

    def get_confirmation_popup_button(self, button_name: str) -> Locator:
        return self.page_menu_popups.locator("div.confirm_container").get_by_role(
            "button", name=button_name
        )

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

    def get_item_in_dropdown_list(
        self, dropdown_button: str, item: str, exact: bool = False
    ) -> Locator:
        return self.dropdown_list(dropdown_button).get_by_role("link", name=item, exact=exact)

    def click_item_in_dropdown_list(
        self, dropdown_button: str, item: str, exact: bool = False
    ) -> None:
        self.dropdown_button(dropdown_button).click()
        expect(self.dropdown_list(dropdown_button)).to_be_visible()
        self.get_item_in_dropdown_list(dropdown_button, item, exact=exact).click()


class Sidebar(LocatorHelper):
    """Functionality to find items from the sidebar"""

    class Snapin:
        """Functionality to find items from the sidebar snapin elements."""

        def __init__(self, base_locator: Locator) -> None:
            self._base_locator = base_locator
            self.container.wait_for(state="attached")

        @property
        def container(self) -> Locator:
            """Returns the container of the snapin."""
            return self._base_locator

        @property
        def loading_spinner(self) -> Locator:
            """Returns the loading spinner displayed when the snapin is loading."""
            return self._base_locator.locator("div.loading")

        @property
        def error_message(self) -> Locator:
            """Returns the error message displayed when an error occurs."""
            return self._base_locator.locator("div.message.error")

        @property
        def close_button(self) -> Locator:
            """Returns the close button of the snapin."""
            return self._base_locator.locator("div.closesnapin a")

        def get_button(self, name: str) -> Locator:
            """Returns the footnote link with the specified text.

            Args:
                name: The text of the button to find.
            """
            return self._base_locator.locator("div.footnotelink >> a").get_by_text(name)

        def remove_from_sidebar(self) -> None:
            """Removes the snapin and waits for it to be detached."""
            self.close_button.click()
            self.container.wait_for(state="detached")

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
    ) -> Locator:
        if not selector:
            selector = "xpath=."
        _loc = self.page.locator("#check_mk_sidebar").locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        return _loc

    def snapin(self, snapin_container_id: str) -> "Snapin":
        return self.Snapin(self.locator(f"div#{snapin_container_id}"))


class FilterSidebar(LocatorHelper):
    """Functionality to find items from the filter sidebar"""

    @override
    def locator(
        self,
        selector: str | None = None,
        *,
        has_text: Pattern[str] | str | None = None,
        has_not_text: Pattern[str] | str | None = None,
        has: Locator | None = None,
        has_not: Locator | None = None,
        check: bool = True,
    ) -> Locator:
        _loc = self._iframe_locator.locator("div#popup_filters")
        if selector:
            _loc = _loc.locator(selector)
        kwargs = self._build_locator_kwargs(
            has_text=has_text,
            has_not_text=has_not_text,
            has=has,
            has_not=has_not,
        )
        _loc = _loc.filter(**kwargs) if kwargs else _loc
        if check:
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

    def filter_button(self, filter_name: str, exact: bool = False) -> Locator:
        return self.filters_list.get_by_role("link", name=filter_name, exact=exact)

    @property
    def select_service_field(self) -> Locator:
        return self.locator("#select2-service_regex-container")

    @property
    def search_text_field(self) -> Locator:
        return self._iframe_locator.get_by_role("searchbox")

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
        return self._iframe_locator.get_by_role("option", name=option_name, exact=exact)

    def filter_combobox(self, filter_name: str, check: bool = True) -> Locator:
        return self.locator("div.floatfilter", has_text=filter_name, check=check).get_by_role(
            "combobox"
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
        logger.info("Set service name=%s", service_filter)
        self.search_text_field.fill(service_filter)
        self.dropdown_option(service_filter, exact=True).click()

    def apply_host_filter(self, host_filter: str) -> None:
        self.select_host_field.click()
        logger.info("Set host name=%s", host_filter)
        self.search_text_field.fill(host_filter)
        # TODO: remove 'first' after fixing CMK-19975
        self.dropdown_option(host_filter, exact=True).first.click()

    def apply_filter_by_name(
        self, filter_name: str, filter_value: str, exact: bool = False
    ) -> None:
        filter_combobox = self.filter_combobox(filter_name, check=False)

        if filter_combobox.count() == 0:
            self.add_filter_button.click()
            self.filter_button(filter_name, exact=exact).click()

        filter_combobox.click()
        self.search_text_field.fill(filter_value)
        # TODO: remove 'first' after fixing CMK-19975
        self.dropdown_option(filter_value, exact=True).first.click()

    def apply_filters(self, expected_locator: Locator) -> None:
        logger.info("Apply filters")
        self.apply_filters_button.click()
        self.page.wait_for_load_state("load")
        expect(expected_locator).to_be_visible()
