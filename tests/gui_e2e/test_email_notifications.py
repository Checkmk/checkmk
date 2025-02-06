#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

import pytest

from tests.gui_e2e.testlib.playwright.plugin import manage_new_page_from_browser_context
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.email import EmailPage
from tests.gui_e2e.testlib.playwright.pom.monitor.service_search import ServiceSearchPage
from tests.gui_e2e.testlib.playwright.pom.setup.add_rule_filesystems import AddRuleFilesystems
from tests.gui_e2e.testlib.playwright.pom.setup.notification_configuration import (
    NotificationConfiguration,
)
from tests.gui_e2e.testlib.playwright.pom.setup.notification_rules import (
    AddNotificationRule,
    EditNotificationRule,
)
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset

from tests.testlib.emails import EmailManager
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.mark.xfail(reason="CMK-21678; investigate web-elements.")
def test_filesystem_email_notifications(
    dashboard_page: Dashboard,
    linux_hosts: list[str],
    notification_user: tuple[str, str],
    email_manager: EmailManager,
    test_site: Site,
    tmp_path: Path,
) -> None:
    """Test that email notification is sent and contain expected data.

    Test that when email notifications are set up and the status of 'Filesystem /' service changes,
    the email notification is sent and contains the expected data.
    """
    email_manager.temp_folder = tmp_path
    username, email = notification_user
    host_name = linux_hosts[0]
    service_name = "Filesystem /"
    expected_event = "OK -> WARN"
    expected_notification_subject = f"Checkmk: {host_name}/{service_name} {expected_event}"
    filesystem_rule_description = "Test rule for email notifications"
    used_space = "10"
    notification_description = "Test rule for email notifications"

    logger.info("Clone the existing default notification rule")
    notification_configuration_page = NotificationConfiguration(dashboard_page.page)
    # The scrollbar interrupts the interaction with rule edit button -> collapse overview
    notification_configuration_page.collapse_notification_overview(True)
    notification_configuration_page.notification_rule_copy_button(0).click()

    logger.info("Modify the cloned rule")
    add_notification_rule_page = AddNotificationRule(
        notification_configuration_page.page, navigate_to_page=False
    )
    add_notification_rule_page.modify_notification_rule(
        username, f"{service_name}$", notification_description
    )

    logger.info("Disable the default notification rule")
    edit_notification_rule_page = EditNotificationRule(
        notification_configuration_page.page, rule_position=0
    )
    edit_notification_rule_page.check_disable_rule(True)
    edit_notification_rule_page.apply_and_create_another_rule_button.click()

    logger.info(
        "Add rule for filesystems to change status '%s' when used space is more then %s percent",
        expected_event,
        used_space,
    )
    add_rule_filesystem_page = AddRuleFilesystems(dashboard_page.page)
    add_rule_filesystem_page.check_levels_for_user_free_space(True)
    add_rule_filesystem_page.description_text_field.fill(filesystem_rule_description)
    add_rule_filesystem_page.levels_for_used_free_space_warning_text_field.fill(used_space)
    add_rule_filesystem_page.save_button.click()
    add_rule_filesystem_page.activate_changes()

    service_search_page = None
    try:
        service_search_page = ServiceSearchPage(dashboard_page.page)
        logger.info("Reschedule the 'Check_MK' service to trigger the notification")
        service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
        service_search_page.reschedule_check(host_name, "Check_MK")
        service_summary = service_search_page.wait_for_check_status_update(
            host_name, service_name, "warn/crit at"
        )

        email_file_path = email_manager.wait_for_email(expected_notification_subject)
        expected_fields = {"To": email}
        expected_content = {
            "Host": host_name,
            "Service": service_name,
            "Event": expected_event,
            "Address": test_site.http_address,
            "Summary": service_summary.replace("WARN", "(!)"),
        }
        email_manager.check_email_content(email_file_path, expected_fields, expected_content)

        html_file_path = email_manager.copy_html_content_into_file(email_file_path)
        expected_content["Event"] = "OK–›WARN"
        expected_content["Summary"] = service_summary

        notification_configuration_page.navigate()
        # The notifications stats need to be read -> open overview
        notification_configuration_page.collapse_notification_overview(False)
        notification_configuration_page.check_total_sent_notifications_is_not_zero()
        notification_configuration_page.check_failed_notifications_is_zero()

        with manage_new_page_from_browser_context(service_search_page.page.context) as new_page:
            email_page = EmailPage(new_page, html_file_path)
            email_page.check_table_content(expected_content)

    finally:
        logger.info("Delete the created rule")
        notification_configuration_page.navigate()
        # The scrollbar interrupts the interaction with rule delete button -> collapse overview
        notification_configuration_page.collapse_notification_overview(True)
        notification_configuration_page.delete_notification_rule(notification_description)

        logger.info("Enable the default notification rule")
        edit_notification_rule_page = EditNotificationRule(
            notification_configuration_page.page, rule_position=0
        )
        edit_notification_rule_page.check_disable_rule(False)
        edit_notification_rule_page.apply_and_create_another_rule_button.click()

        if service_search_page is not None:
            filesystems_rules_page = Ruleset(
                service_search_page.page,
                "Filesystems (used space and growth)",
                "Service monitoring rules",
            )
            logger.info("Delete the filesystems rule")
            filesystems_rules_page.delete_rule(rule_id=filesystem_rule_description)
            filesystems_rules_page.activate_changes()
