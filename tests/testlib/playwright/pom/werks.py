#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.playwright.helpers import PPage


class Werks(PPage):
    page_title: str = "Change log (Werks)"

    def __init__(
        self,
        ppage: PPage,
    ):
        super().__init__(ppage.page, ppage.site_id, ppage.site_url)
        self.click_and_wait(self.main_menu.help_werks, navigate=True)
        self.main_area.check_page_title(self.page_title)
        self.main_area.page.wait_for_load_state("networkidle")

    def get_recent_werks(self, count: int = 100) -> dict[int, str]:
        self.main_area.locator("#menu_suggestion_filters").click()
        filter_popup = self.main_area.locator("#popup_filters")
        filter_popup.locator("#wo_grouping").select_option(label="Day of creation")
        self.click_and_wait(filter_popup.locator("#apply"), navigate=True)

        links = self.main_area.locator("a").get_by_text("#").element_handles()[:count]
        werks = {
            int(str(link.text_content())[1:]): str(link.get_attribute("href")) for link in links
        }

        return werks
