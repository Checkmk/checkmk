#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.email import EmailPage
from tests.gui_e2e.testlib.playwright.pom.monitor.service_search import (
    ServiceSearchPage,
    ServiceState,
)
from tests.gui_e2e.testlib.playwright.pom.setup.add_rule_filesystems import AddRuleFilesystems
from tests.gui_e2e.testlib.playwright.pom.setup.notification_configuration import (
    NotificationConfiguration,
)
from tests.gui_e2e.testlib.playwright.pom.setup.notification_rules import EditNotificationRule
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset
from tests.testlib.emails import EmailManager
from tests.testlib.site import Site
from tests.testlib.utils import run

logger = logging.getLogger(__name__)


def _copy_file(
    src: Path,
    dst: Path,
) -> None:
    """Copy file from src to dst."""
    try:
        run(["cp", "-f", str(src), str(dst)], sudo=True)
    except subprocess.CalledProcessError as exception:
        exception.add_note(f"Failed to copy '{src}' to '{dst}'!")
        raise exception


@pytest.fixture(name="modify_notification_rule", scope="function")
def _modify_notification_rule(test_site: Site, linux_hosts: list[str]) -> Iterator[str]:
    """Modify existing email notification rule to match a specific host.

    * Copy the existing notification rule file to a backup
    * Modify the notification rule to match a specific host
    * Restore the original notification rule file after the test execution
    """
    hostname = linux_hosts[0]

    notification_rule_path = test_site.path("etc/check_mk/conf.d/wato/notifications.mk")
    notification_rule_backup_path = notification_rule_path.parent / "notifications.mk.bak"
    _copy_file(notification_rule_path, notification_rule_backup_path)

    try:
        content = test_site.read_file(notification_rule_path)
        new_content = content[:-3] + f", 'match_hosts': ['{hostname}']" + content[-3:]
        test_site.write_file(notification_rule_path, new_content)

        yield hostname

    finally:
        _copy_file(notification_rule_backup_path, notification_rule_path)
        test_site.delete_file(notification_rule_backup_path)


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
    notification_configuration_page.collapse_notification_overview(False)
    total_sent = notification_configuration_page.get_total_sent_notifications_count()
    total_failures = notification_configuration_page.get_failed_notifications_count()
    logger.info("Current notification stats: sent=%s, failed=%s", total_sent, total_failures)
    # The scrollbar interrupts the interaction with rule edit button -> collapse overview
    notification_configuration_page.collapse_notification_overview(True)
    notification_configuration_page.notification_rule_copy_button(0).click()
    notification_configuration_page.clone_and_edit_button.click()

    try:
        service_search_page = None

        logger.info("Modify the cloned rule")
        cloned_notification_rule_page = EditNotificationRule(
            notification_configuration_page.page,
            rule_position=1,
            navigate_to_page=False,
        )
        cloned_notification_rule_page.modify_notification_rule(
            username, f"{service_name}$", notification_description
        )

        logger.info("Disable the default notification rule")
        default_notification_rule_page = EditNotificationRule(
            notification_configuration_page.page, rule_position=0
        )
        default_notification_rule_page.check_disable_rule(True)
        default_notification_rule_page.apply_and_create_another_rule_button.click()

        logger.info(
            (
                "Add rule for filesystems to change status '%s'"
                " when used space is more than %s percent"
            ),
            expected_event,
            used_space,
        )
        add_rule_filesystem_page = AddRuleFilesystems(dashboard_page.page)
        add_rule_filesystem_page.check_levels_for_user_free_space(True)
        add_rule_filesystem_page.description_text_field.fill(filesystem_rule_description)
        add_rule_filesystem_page.levels_for_used_free_space_warning_text_field.fill(used_space)
        add_rule_filesystem_page.select_explicit_host(host_name)
        add_rule_filesystem_page.save_button.click()
        add_rule_filesystem_page.activate_changes(test_site)

        checkmk_agent = "Check_MK"
        service_search_page = ServiceSearchPage(dashboard_page.page)
        logger.info("Reschedule the '%s' service to trigger the notification", checkmk_agent)
        service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
        service_search_page.reschedule_check(host_name, checkmk_agent)
        service_search_page.wait_for_check_status_update(host_name, service_name, ServiceState.WARN)
        service_summary = service_search_page.service_summary(host_name, service_name).inner_text()

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
        notification_configuration_page.check_total_sent_notifications_has_changed(total_sent)
        notification_configuration_page.check_failed_notifications_has_not_changed(total_failures)

        new_page = dashboard_page.page.context.new_page()
        email_page = EmailPage(new_page, html_file_path)
        email_page.check_table_content(expected_content)
        new_page.close()

    finally:
        if service_search_page is not None:
            filesystems_rules_page = Ruleset(
                service_search_page.page,
                "Filesystems (used space and growth)",
                "Service monitoring rules",
            )
            logger.info("Delete the filesystems rule")
            filesystems_rules_page.delete_rule(rule_id=filesystem_rule_description)
            filesystems_rules_page.activate_changes(test_site)

            # Expect for the service to be OK after rule removal
            service_search_page.navigate()
            service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
            service_search_page.reschedule_check(host_name, checkmk_agent)
            service_search_page.wait_for_check_status_update(
                host_name, service_name, ServiceState.OK
            )

        logger.info("Delete the created rule")

        if not notification_configuration_page.is_the_current_page():
            notification_configuration_page.navigate()

        # The scrollbar interrupts the interaction with rule delete button -> collapse overview
        notification_configuration_page.collapse_notification_overview(True)
        # delete the cloned rule.
        notification_configuration_page.delete_notification_rule(rule_id=1)

        logger.info("Enable the default notification rule")
        default_notification_rule_page = EditNotificationRule(
            notification_configuration_page.page,
            rule_position=0,
            navigate_to_notification_configuration=False,
        )
        default_notification_rule_page.check_disable_rule(False)
        default_notification_rule_page.apply_and_create_another_rule_button.click()

        email_manager.clean_emails(expected_notification_subject)


def test_email_notifications_host_filters(
    modify_notification_rule: str,
    dashboard_page: Dashboard,
) -> None:
    """Test to verify that the host filter is working as expected.

    * Modify existing notification rule located in ~/etc/check_mk/conf.d/wato/notifications.mk
      so that to match the rule for a specific host
    * Verify the match host is displayed under "Conditions" in
      Setup > Events > Notifications > Events > Test notifications
    * Verify the match host is displayed when modifying the existing rule under "Host filters"
    * Restore the notification rule to its original state
    """
    host_name = modify_notification_rule
    notification_configuration_page = NotificationConfiguration(dashboard_page.page)

    # pre-condition for this test to be successful
    expect(
        notification_configuration_page.notification_rule_rows,
        message="Only one notification rule expected",
    ).to_have_count(1)

    notification_configuration_page.expand_conditions()

    expect(
        notification_configuration_page.notification_rule_condition(
            rule_number=0, condition_name="Match hosts:"
        ),
        message=f"Expected host '{host_name}' in rule conditions",
    ).to_have_text(host_name)

    edit_notification_rule_page = EditNotificationRule(
        notification_configuration_page.page,
        rule_position=0,
        navigate_to_notification_configuration=False,
    )
    edit_notification_rule_page.expand_host_filters()
    edit_notification_rule_page.hosts_dropdown_list().click()
    expect(
        edit_notification_rule_page.hosts_dropdown_list(),
        message=f"Expected rule to be filtered by host: '{host_name}'",
    ).to_contain_text(host_name)
