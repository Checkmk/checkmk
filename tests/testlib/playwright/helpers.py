#!/usr/bin/env python
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper for a page, with some often used functionality"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal, Optional
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import expect, Locator, Page, Response

from tests.testlib.playwright.timeouts import TemporaryTimeout, TIMEOUT_ACTIVATE_CHANGES_MS


class LocatorHelper(ABC):
    """base class for helper classes for certain page elements"""

    def __init__(self, page: Page) -> None:
        self.page = page

    @abstractmethod
    def locator(self, selector: str = "xpath=.") -> Locator:
        """return locator for this subpart"""

    def check_success(self, message: str) -> None:
        """check for a success div and its content"""
        expect(self.locator("div.success")).to_have_text(message)

    def check_error(self, message: str) -> None:
        """check for an error div and its content"""
        expect(self.locator("div.error")).to_have_text(message)

    def get_input(self, input_name: str) -> Locator:
        return self.locator(f'input[name="{input_name}"]')

    def get_suggestion(self, suggestion: str) -> Locator:
        return self.locator(f"#suggestions >> text={suggestion}")

    def get_text(self, text: str) -> Locator:
        return self.locator(f"text={text}")

    def get_element_including_texts(self, element_id: str, texts: list[str]) -> Locator:
        has_text_str = "".join([f":has-text('{t}')" for t in texts])
        return self.locator(f"#{element_id}{has_text_str}")

    def get_link_from_title(self, title: str) -> Locator:
        return self.locator(f"a[title='{title}']")

    def get_attribute_label(self, attribute: str) -> Locator:
        return self.locator(f"#attr_{attribute} label")


class Keys(Enum):
    """Keys to control the virtual keyboard in playwright."""

    Enter = "Enter"
    Escape = "Escape"
    ArrowUp = "ArrowUp"
    ArrowDown = "ArrowDown"
    ArrowLeft = "ArrowLeft"
    ArrowRight = "ArrowRight"


class MainMenu(LocatorHelper):
    """functionality to find items from the main menu"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator("#check_mk_navigation").locator(selector)

    @property
    def user(self) -> Locator:
        """main menu -> User"""
        return self.locator("a.popup_trigger:has-text('User')")

    @property
    def user_menu(self) -> Locator:
        """main menu -> User menu"""
        user_menu_locator = self.locator("#popup_trigger_mega_menu_user")
        classes = str(user_menu_locator.get_attribute("class")).split(" ")
        if "active" not in classes:
            self.user.click()
        return self.locator("#popup_menu_user")

    @property
    def user_color_theme(self) -> Locator:
        return self.user_menu.get_by_text("Color theme")

    @property
    def user_color_theme_button(self) -> Locator:
        return self.user_menu.locator("#ui_theme")

    @property
    def user_sidebar_position(self) -> Locator:
        return self.user_menu.get_by_text("Sidebar position")

    @property
    def user_sidebar_position_button(self) -> Locator:
        return self.user_menu.locator("#sidebar_position")

    @property
    def user_edit_profile(self) -> Locator:
        return self.user_menu.get_by_text("Edit profile")

    @property
    def user_notification_rules(self) -> Locator:
        return self.user_menu.get_by_text("Notification rules")

    @property
    def user_change_password(self) -> Locator:
        return self.user_menu.get_by_text("Change password")

    @property
    def user_two_factor_authentication(self) -> Locator:
        return self.user_menu.get_by_text("Two-factor authentication")

    @property
    def user_logout(self) -> Locator:
        return self.user_menu.get_by_text("Logout")

    @property
    def help(self) -> Locator:
        """main menu -> Help"""
        return self.locator('text="Help"')

    @property
    def help_menu(self) -> Locator:
        """main menu -> Help menu"""
        help_menu_locator = self.locator("#popup_trigger_mega_menu_help_links")
        classes = str(help_menu_locator.get_attribute("class")).split(" ")
        if "active" not in classes:
            self.help.click()
        return self.locator("#popup_menu_help_links")

    @property
    def help_beginners_guide(self) -> Locator:
        return self.help_menu.get_by_text("Beginner's guide")

    @property
    def help_user_manual(self) -> Locator:  #
        return self.help_menu.get_by_text("User manual")

    @property
    def help_video_tutorials(self) -> Locator:
        return self.help_menu.get_by_text("Video tutorials")

    @property
    def help_community_forum(self) -> Locator:
        return self.help_menu.get_by_text("Community forum")

    @property
    def help_plugin_api_intro(self) -> Locator:
        return self.help_menu.get_by_text("Check plugin API introduction")

    @property
    def help_plugin_api_docs(self) -> Locator:
        return self.help_menu.get_by_text("Check plugin API reference")

    @property
    def help_rest_api_intro(self) -> Locator:
        return self.help_menu.get_by_text("REST API introduction")

    @property
    def help_rest_api_docs(self) -> Locator:
        return self.help_menu.get_by_text("REST API documentation")

    @property
    def help_rest_api_gui(self) -> Locator:
        return self.help_menu.get_by_text("REST API interactive GUI")

    @property
    def help_info(self) -> Locator:
        return self.help_menu.get_by_text("Info")

    @property
    def help_werks(self) -> Locator:
        return self.help_menu.get_by_text("Change log (Werks)")


class MainFrame(LocatorHelper):
    """functionality to find items from the main frame"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.frame_locator("iframe[name='main']").locator(selector)

    def check_page_title(self, title: str) -> None:
        """check the page title"""
        expect(self.locator("div.titlebar > a")).to_have_text(title)


class Sidebar(LocatorHelper):
    """functionality to find items from the sidebar"""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator("#check_mk_sidebar").locator(selector)


class PPage(LocatorHelper):
    """Playwright Page, wrapper around the page"""

    def __init__(
        self,
        page: Page,
        site_id: str,
        site_url: Optional[str] = None,
    ) -> None:
        super().__init__(page)
        self.main_menu = MainMenu(self.page)
        self.main_frame = MainFrame(self.page)
        self.sidebar = Sidebar(self.page)
        self.site_id = site_id
        if site_url:
            self.site_url = site_url
        else:
            self.site_url = "".join(urlsplit(self.page.url)[0:2])
        self.username = ""
        self.password = ""

    def locator(self, selector: str = "xpath=.") -> Locator:
        return self.page.locator(selector)

    def login(self, username: str = "", password: str = "") -> None:
        """login to cmk"""
        if not username:
            username = self.username
        if not password:
            password = self.password
        self.page.locator("#input_user").fill(username)
        self.page.locator("#input_pass").fill(password)
        self.page.locator("#_login").click()
        self.username = username
        self.password = password

    def logout(self) -> None:
        self.main_menu.user_logout.click()

    def activate_selected(self) -> None:
        with TemporaryTimeout(self.page, TIMEOUT_ACTIVATE_CHANGES_MS):
            return self.main_frame.locator("#menu_suggestion_activate_selected").click()

    def expect_success_state(self) -> None:
        expect(
            self.main_frame.locator("#site_gui_e2e_central_status.msg.state_success")
        ).to_be_visible()

        expect(
            self.main_frame.locator("#site_gui_e2e_central_progress.progress.state_success")
        ).to_be_visible()

        # assert no further changes are pending
        expect(self.main_frame.locator("div.page_state.no_changes")).to_be_visible(
            timeout=TIMEOUT_ACTIVATE_CHANGES_MS
        )

    @property
    def megamenu_setup(self) -> Locator:
        return self.main_menu.locator("#popup_trigger_mega_menu_setup")

    def goto_setup_hosts(self) -> None:
        """main menu -> setup -> Hosts"""
        self.megamenu_setup.click()
        return self.main_menu.locator('#setup_topic_hosts a:has-text("Hosts")').click()

    @property
    def megamenu_monitoring(self) -> Locator:
        return self.main_menu.locator("#popup_trigger_mega_menu_monitoring")

    @property
    def monitor_searchbar(self) -> Locator:
        return self.megamenu_monitoring.locator("#mk_side_search_field_monitoring_search")

    def goto_monitoring_all_hosts(self) -> None:
        """main menu -> monitoring -> All hosts"""
        monitoring = self.megamenu_monitoring
        monitoring.click()

        all_hosts = self.megamenu_monitoring.locator("#monitoring_topic_overview >> text=All hosts")
        all_hosts.wait_for()
        all_hosts.click()

    def select_host(self, host_name: str) -> None:
        self.main_frame.locator(f"td:has-text('{host_name}')").click()

    def goto_add_sidebar_element(self) -> None:
        self.locator("div#check_mk_sidebar >> div#add_snapin > a").click()
        self.main_frame.check_page_title("Add sidebar element")

    def press_keyboard(self, key: Keys) -> None:
        self.page.keyboard.press(str(key.value))

    def go(
        self,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        wait_until: Optional[Literal["commit", "domcontentloaded", "load", "networkidle"]] = None,
        referer: Optional[str] = None,
    ) -> Optional[Response]:
        """calls page.goto() but will accept relative urls"""
        return self.page.goto(
            urljoin(self.site_url, url), timeout=timeout, wait_until=wait_until, referer=referer
        )

    def click_and_wait(self, locator: Locator, navigate: bool = False) -> None:
        """clicks the located element and wait until the current url has changed and is loaded"""
        url = self.page.url
        locator.click()
        if navigate:
            expect(self.page).not_to_have_url(url)
        self.page.wait_for_load_state("networkidle")
