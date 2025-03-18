#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import pytest
from playwright.sync_api import expect
from playwright.sync_api import TimeoutError as PWTimeoutError

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.werks import Werks

logger = logging.getLogger(__name__)


@pytest.fixture(name="werks_page", scope="function")
def fixture_werks_page(dashboard_page: Dashboard) -> Iterator[Werks]:
    yield Werks(dashboard_page.page)


def test_werks_available(werks_page: Werks) -> None:
    displayed_werks = werks_page.get_recent_werks(count=5)
    displayed_werk_ids = list(displayed_werks.keys())
    assert len(displayed_werk_ids) > 0, "Checkmk site does not display any werks!"

    for werk_id in displayed_werks:
        _url_pattern: str = quote_plus(f"werk.py?werk={werk_id}")
        werks_page.werk(werk_id).click()
        werks_page.page.wait_for_url(re.compile(f"{_url_pattern}$"), wait_until="load")
        werks_page.page.go_back(wait_until="load")


@pytest.mark.skip(reason="CMK-22461; incomplete validation.")
def test_navigate_to_werks(werks_page: Werks) -> None:
    # validate presence of dropdown buttons
    for button_name in werks_page.dropdown_buttons:
        expect(werks_page.main_area.dropdown_button(button_name)).to_be_visible()

    # validate 'Filter' button works
    werks_page.get_link("Filter").click()
    expect(
        werks_page.main_area.locator().get_by_role(role="heading", name="Filter")
    ).to_be_visible()
    expect(werks_page.apply_filter).to_have_count(1)
    expect(werks_page.reset_filter).to_have_count(1)

    # validate 'Acnowledge all' button is disabled
    with pytest.raises(PWTimeoutError):
        werks_page.get_link("Acknowledge all").click()

    # validate presence of Werks
    max_number_of_werks_displayed = 100
    number_of_werks_displayed = werks_page.get_link("#", exact=False).count()
    assert number_of_werks_displayed > 0, "Checkmk site does not display any werks!"
    assert (
        number_of_werks_displayed <= max_number_of_werks_displayed
    ), f"Checkmk site displays a maximum of {max_number_of_werks_displayed} werks, by default!"
