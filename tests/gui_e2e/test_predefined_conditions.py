#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator

import pytest

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.predefined_conditions import AddPredefinedCondition

logger = logging.getLogger(__name__)


@pytest.fixture(name="add_predefined_condition_page", scope="function")
def fixture_add_predefined_condition_page(
    dashboard_page: Dashboard,
) -> Iterator[AddPredefinedCondition]:
    yield AddPredefinedCondition(dashboard_page.page)


def test_add_predefined_condition(
    add_predefined_condition_page: AddPredefinedCondition,
) -> None:
    add_predefined_condition_page.add_condition_to_host_label_button.click()
    add_predefined_condition_page.add_host_label("is", "a:b")
    add_predefined_condition_page.save_predefined_condition_button.click()
    # TODO:remove breakpoint
    breakpoint()
    # TODO: validate the error message; use 'check_error("error message")'
    # TODO: validate that the given label is still there;
    # HINT: use 'expect(Locator, message="err message").to_have_text()'
