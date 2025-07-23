#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.notification_rules import AddNotificationRule


@pytest.mark.skip_if_not_edition("saas")
def test_saas_quick_setup_hides_explicit_email_addresses(dashboard_page: Dashboard) -> None:
    notification_rule_page = AddNotificationRule(dashboard_page.page)

    notification_rule_page.ensure_guided_mode()
    notification_rule_page.main_area.check_page_title("Add notification rule")

    # Move to step 2 (Filter for hosts/services)
    notification_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=1)

    # Move to step 3 (Notification method (plug-in))
    notification_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=2)

    notification_rule_page.select_notification_effect("Suppress all previous")

    # Move to step 4 (Recipient)
    notification_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=3)
    dropdown = notification_rule_page.select_recipient_dropdown(0)
    dropdown.click()
    explicit_email_option = notification_rule_page.select_recipient_option(
        "Explicit email addresses"
    )
    expect(explicit_email_option).to_have_count(0)


@pytest.mark.skip_if_edition("saas")
def test_non_saas_quick_setup_shows_explicit_email_addresses(dashboard_page: Dashboard) -> None:
    notification_rule_page = AddNotificationRule(dashboard_page.page)

    notification_rule_page.ensure_guided_mode()
    notification_rule_page.main_area.check_page_title("Add notification rule")

    # Move to step 2 (Filter for hosts/services)
    notification_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=1)

    # Move to step 3 (Notification method (plug-in))
    notification_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=2)

    notification_rule_page.select_notification_effect("Suppress all previous")

    # Move to step 4 (Recipient)
    notification_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=3)
    dropdown = notification_rule_page.select_recipient_dropdown(0)
    dropdown.click()
    explicit_email_option = notification_rule_page.select_recipient_option(
        "Explicit email addresses"
    )
    expect(explicit_email_option).to_have_count(1)
