#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from abc import abstractmethod
from typing import Literal, overload
from urllib.parse import urljoin

from playwright.sync_api import expect, FrameLocator, Locator, Page, Response

from tests.testlib.playwright.helpers import Keys, LocatorHelper

logger = logging.getLogger(__name__)


class CmkPage(LocatorHelper):
    """Parent object representing a Checkmk GUI page."""

    def __init__(
        self,
        page: Page,
        navigate_to_page: bool = True,
        timeout_assertions: int | None = None,
        timeout_navigation: int | None = None,
    ) -> None:
        super().__init__(page, timeout_assertions, timeout_navigation)
        self._navigate_to_page = navigate_to_page
        self.main_menu = MainMenu(self.page)
        self.main_area = MainArea(self.page)
        self.sidebar = Sidebar(self.page)
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
        logger.info("Press keyboard key: %d", key.value)
        self.page.keyboard.press(str(key.value))

    def get_link(self, name: str, exact: bool = True) -> Locator:
        """Returns a web-element from the `main_area`, which is a `link`."""
        return self.main_area.locator().get_by_role(role="link", name=name, exact=exact)

    def goto(self, url: str, event: str = "load") -> None:
        """Override `Page.goto`. Additionally, wait for the page to `load`, by default.

        The `event` to be expected can be changed.
        """
        with self.page.expect_event(event) as _:
            self.page.goto(url)

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

    def dropdown_button(self, name: str, exact: bool = True) -> Locator:
        return self.main_area.locator().get_by_role(role="heading", name=name, exact=exact)


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
    def help_werks(self) -> Locator:
        return self.help_menu("Change log (Werks)")

    def logout(self) -> None:
        logger.info("Click logout button")
        self.user_logout.click()
        self.page.wait_for_url(url=re.compile("login.py$"), wait_until="load")


class MainArea(LocatorHelper):
    """functionality to find items from the main area"""

    @overload
    def locator(self, selector: None = None) -> FrameLocator: ...

    @overload
    def locator(self, selector: str) -> Locator: ...

    def locator(self, selector: str | None = None) -> Locator | FrameLocator:
        _loc = self.page.frame_locator("iframe[name='main']")
        if selector is None:
            return _loc
        return _loc.locator(selector)

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
