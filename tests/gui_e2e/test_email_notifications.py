#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.testlib.emails import EmailManager
from tests.testlib.playwright.plugin import manage_new_page_from_browser_context
from tests.testlib.playwright.pom.dashboard import Dashboard
from tests.testlib.playwright.pom.email import EmailPage
from tests.testlib.playwright.pom.monitor.service_search import ServiceSearchPage
from tests.testlib.playwright.pom.setup.add_rule_filesystems import AddRuleFilesystems
from tests.testlib.playwright.pom.setup.edit_notification_rule import EditNotificationRule
from tests.testlib.playwright.pom.setup.ruleset import Ruleset
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="email_manager", scope="module")
def create_email_manager() -> Iterator[EmailManager]:
    """Create EmailManager instance.

    EmailManager handles setting up and tearing down Postfix SMTP-server, which is configured
    to redirect emails to a local Maildir. It also provides methods to check and wait for emails.
    """
    with EmailManager() as email_manager:
        yield email_manager


@pytest.fixture(name="notification_user", scope="module")
def create_notification_user(test_site: Site) -> Iterator[tuple[str, str]]:
    """Create a user for email notifications via API.

    Create a user with email in order to receive email notifications.
    Delete the user after the test.
    """
    faker = Faker()
    username = faker.user_name()
    email = f"{username}@test.com"

    test_site.openapi.create_user(
        username=username,
        fullname=faker.name(),
        password=faker.password(length=12),
        email=email,
        contactgroups=["all"],
        customer="global" if test_site.version.is_managed_edition() else None,
    )
    test_site.openapi.activate_changes_and_wait_for_completion()
    yield username, email
    test_site.openapi.delete_user(username)
    test_site.openapi.activate_changes_and_wait_for_completion()


@pytest.mark.parametrize(
    "create_host_using_agent_dump",
    [
        pytest.param(
            ("linux-2.4.0-2024.08.27", [f"{Faker().hostname()}"]),
            id="filesystem_email_notifications",
        ),
    ],
    indirect=["create_host_using_agent_dump"],
)
def test_filesystem_email_notifications(
    dashboard_page: Dashboard,
    create_host_using_agent_dump: list[str],
    notification_user: tuple[str, str],
    email_manager: EmailManager,
    test_site: Site,
) -> None:
    """Test that email notification is sent and contain expected data.

    Test that when email notifications are set up and the status of 'Filesystem /' service changes,
    the email notification is sent and contains the expected data.
    """
    username, email = notification_user
    host_name = create_host_using_agent_dump[0]
    service_name = "Filesystem /"
    expected_event = "OK -> WARN"
    expected_notification_subject = f"Check_MK: {host_name}/{service_name} {expected_event}"
    filesystem_rule_description = "Test rule for email notifications"
    used_space = "10"

    edit_notification_rule_page = EditNotificationRule(dashboard_page.page, 0)
    edit_notification_rule_page.modify_notification_rule([username], [f"{service_name}$"])

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
        service_search_page.apply_filters_button.click()
        expect(service_search_page.services_table).to_be_visible()
        service_search_page.reschedule_check("Check_MK")
        service_summary = service_search_page.service_summary(service_name).inner_text()

        email_file_path = email_manager.wait_for_email(expected_notification_subject)
        expected_fields = {"To": email}
        expected_content = {
            "Host": host_name,
            "Service": service_name,
            "Event": expected_event,
            "Address": test_site.http_address,
            "Summary": service_summary.replace(
                ",", f" (warn/crit at {float(used_space):.2f}%/90.00% used)(!),", 1
            ),
        }
        email_manager.check_email_content(email_file_path, expected_fields, expected_content)

        html_file_path = email_manager.copy_html_content_into_file(email_file_path)
        expected_content["Event"] = "OK → WARNING"
        expected_content["Summary"] = expected_content["Summary"].replace("(!)", "WARN", 1)

        with manage_new_page_from_browser_context(service_search_page.page.context) as new_page:
            email_page = EmailPage(new_page, html_file_path)
            email_page.check_table_content(expected_content)

    finally:
        edit_notification_rule_page.navigate()
        edit_notification_rule_page.restore_notification_rule(True, True)

        if service_search_page is not None:
            filesystems_rules_page = Ruleset(
                service_search_page.page,
                "Filesystems (used space and growth)",
                "Service monitoring rules",
            )
            logger.info("Delete the filesystems rule")
            filesystems_rules_page.delete_rule(rule_id=filesystem_rule_description)
            filesystems_rules_page.activate_changes()
