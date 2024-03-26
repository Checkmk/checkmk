#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from playwright.sync_api import Error, expect, Locator, Page
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.testlib.playwright.helpers import Keys, LocatorHelper
from tests.testlib.playwright.timeouts import TemporaryTimeout, TIMEOUT_ACTIVATE_CHANGES_MS


class MainMenu(LocatorHelper):
    """functionality to find items from the main menu"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator("#check_mk_navigation").locator(selector)

    @property
    def main_page(self) -> Locator:
        return self.locator('a[title="Go to main page"]')

    def _sub_menu(self, menu: str, menu_id: str, item: str | None, show: bool = True) -> Locator:
        """main menu -> sub menu"""
        menu_locator = self.locator(f"#{menu_id}")
        classes = str(menu_locator.get_attribute("class")).split(" ")
        if ("active" in classes) != show:
            # show/hide menu
            self.locator("a.popup_trigger").filter(has=self.page.locator(f'text="{menu}"')).click()
        if item:
            item_locator = menu_locator.locator("a").filter(has=self.page.locator(f'text="{item}"'))
            return item_locator
        return menu_locator

    def monitor_menu(self, item: str | None = None, show: bool = True) -> Locator:
        """main menu -> Monitor"""
        return self._sub_menu("Monitor", "popup_trigger_mega_menu_monitoring", item, show)

    def setup_menu(self, item: str | None = None, show: bool = True) -> Locator:
        """main menu -> Setup"""
        return self._sub_menu("Setup", "popup_trigger_mega_menu_setup", item, show)

    def user_menu(self, item: str | None = None, show: bool = True) -> Locator:
        """main menu -> User"""
        return self._sub_menu("User", "popup_trigger_mega_menu_user", item, show)

    def help_menu(self, item: str | None = None, show: bool = True) -> Locator:
        """main menu -> Help"""
        return self._sub_menu("Help", "popup_trigger_mega_menu_help_links", item, show)

    @property
    def monitor_searchbar(self) -> Locator:
        return self.monitor_menu().locator("#mk_side_search_field_monitoring_search")

    @property
    def monitor_all_hosts(self) -> Locator:
        """main menu -> monitoring -> All hosts"""
        return self.monitor_menu("All hosts")

    @property
    def setup_hosts(self) -> Locator:
        return self.setup_menu("Hosts")

    @property
    def user_color_theme(self) -> Locator:
        return self.user_menu("Color theme")

    @property
    def user_color_theme_button(self) -> Locator:
        return self.user_menu().locator("#ui_theme")

    @property
    def user_sidebar_position(self) -> Locator:
        return self.user_menu("Sidebar position")

    @property
    def user_sidebar_position_button(self) -> Locator:
        return self.user_menu().locator("#sidebar_position")

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
    def help_werks(self) -> Locator:
        return self.help_menu("Change log (Werks)")


class MainArea(LocatorHelper):
    """functionality to find items from the main area"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.frame_locator("iframe[name='main']").locator(selector)

    def check_page_title(self, title: str) -> None:
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


class Sidebar(LocatorHelper):
    """functionality to find items from the sidebar"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator("#check_mk_sidebar").locator(selector)


class CmkPage(LocatorHelper):
    """Parent object representing a Checkmk GUI page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url: str
        self.main_menu = MainMenu(self.page)
        self.main_area = MainArea(self.page)
        self.sidebar = Sidebar(self.page)

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator(selector)

    def activate_selected(self) -> None:
        with TemporaryTimeout(self.page, TIMEOUT_ACTIVATE_CHANGES_MS):
            self.main_area.locator("#menu_suggestion_activate_selected").click()

    def expect_success_state(self) -> None:
        expect(
            self.main_area.locator("#site_gui_e2e_central_status.msg.state_success")
        ).to_be_visible(timeout=TIMEOUT_ACTIVATE_CHANGES_MS)

        expect(
            self.main_area.locator("#site_gui_e2e_central_progress.progress.state_success")
        ).to_be_visible(timeout=TIMEOUT_ACTIVATE_CHANGES_MS)

        # assert no further changes are pending
        expect(self.main_area.locator("div.page_state.no_changes")).to_be_visible(
            timeout=TIMEOUT_ACTIVATE_CHANGES_MS
        )

    def goto_main_dashboard(self) -> None:
        """Click the banner and wait for the dashboard"""
        self.main_menu.main_page.click()
        self.main_area.check_page_title("Main dashboard")

    def select_host(self, host_name: str) -> None:
        self.main_area.locator(f"td a:has-text('{host_name}')").click()

    def goto_add_sidebar_element(self) -> None:
        self.locator("div#check_mk_sidebar >> div#add_snapin > a").click()
        self.main_area.check_page_title("Add sidebar element")

    def press_keyboard(self, key: Keys) -> None:
        self.page.keyboard.press(str(key.value))

    def click_and_wait(
        self,
        locator: Locator,
        navigate: bool = False,
        expected_locator: Locator | None = None,
        reload_on_error: bool = False,
        max_tries: int = 10,
    ) -> None:
        """Wait until the specified locator could be clicked.
        After a successful click, wait until the current URL has changed and is loaded
        or an expected locator is found.
        """
        url = self.page.url
        clicked = False

        for _ in range(max_tries):
            if not clicked:
                try:
                    locator.click()
                    clicked = True
                except PWTimeoutError:
                    pass

            if clicked:
                try:
                    if navigate:
                        expect(self.page).not_to_have_url(url)
                    if expected_locator:
                        expect(expected_locator).to_be_visible()
                    self.page.wait_for_load_state("networkidle")
                    return
                except AssertionError:
                    pass

            try:
                if reload_on_error:
                    self.page.reload(wait_until="networkidle")
            except Error:
                continue

        raise AssertionError(
            "Current URL did not change, expected locator not found or page failed to reload."
        )
