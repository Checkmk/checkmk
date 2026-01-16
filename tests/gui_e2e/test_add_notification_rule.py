#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

import pytest

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.monitor.service_search import (
    ServiceSearchPage,
    ServiceState,
)
from tests.gui_e2e.testlib.playwright.pom.setup.add_rule_filesystems import AddRuleFilesystems
from tests.gui_e2e.testlib.playwright.pom.setup.notification_configuration import (
    NotificationConfiguration,
)
from tests.gui_e2e.testlib.playwright.pom.setup.notification_rules import (
    AddNotificationRule,
    EditNotificationRule,
    STAGE_FILTER_HOSTS_SERVICES,
    STAGE_GENERAL_PROPERTIES,
    STAGE_NOTIFICATION_METHOD,
    STAGE_RECIPIENT,
    STAGE_SENDING_CONDITIONS,
    STAGE_TRIGGERING_EVENTS,
)
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset
from tests.testlib.emails import EmailManager
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("notification_user")
def test_add_new_notification_rule(
    dashboard_page: Dashboard,
    linux_hosts: list[str],
    notification_user: tuple[str, str],
    email_manager: EmailManager,
    test_site: Site,
    tmp_path: Path,
) -> None:
    """Test adding a new notification rule creates the expected email"""
    email_manager.temp_folder = tmp_path
    username, email = notification_user
    host_name = linux_hosts[0]
    service_name = "Filesystem /"
    expected_notification_subject = "GUI E2E Test Add Notification Rule"
    filesystem_rule_description = "Test rule for email notifications"
    used_space = "10"

    logger.info("Add new notification rule")

    add_rule_page = AddNotificationRule(dashboard_page.page)

    logger.info("Ensure Guided Mode")
    add_rule_page.ensure_guided_mode()

    logger.info(
        "Skip stage '%s' and go to '%s'", STAGE_TRIGGERING_EVENTS, STAGE_FILTER_HOSTS_SERVICES
    )
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=1)

    logger.info("Set Hosts on Host filters to '%s'", test_site.id)
    add_rule_page.expand_host_filters()
    add_rule_page.hosts_checkbox.set_checked(True)
    add_rule_page.hosts_dropdown_list().click()
    add_rule_page.select_host_from_dropdown_list(host_name).click()

    logger.info("Go to stage '%s'", STAGE_NOTIFICATION_METHOD)
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=2)

    logger.info("Create new html email parameter")
    add_rule_page.create_html_parameter_using_slide_in()

    logger.info("Set description of parameter")
    add_rule_page.si_description.fill("gui_e2e_test_parameter")

    logger.info("Set other values to non default")
    logger.info("Check: Custom Sender (From) > Display name > Fill input")
    add_rule_page.si_custom_sender_checkbox.set_checked(True)

    add_rule_page.si_displayname_checkbox.set_checked(True)
    add_rule_page.si_displayname_input.fill("Automatic GUI E2E Test")
    logger.info("Check: Subject line for host/service notifications > Fill input")
    add_rule_page.si_host_subject_checkbox.set_checked(True)
    add_rule_page.si_host_subject_input.fill(expected_notification_subject)
    add_rule_page.si_service_subject_checkbox.set_checked(True)
    add_rule_page.si_service_subject_input.fill(expected_notification_subject)

    logger.info("Save parameter")
    add_rule_page.save_editor_slide_in()

    logger.info("Go to stage '%s'", STAGE_RECIPIENT)
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=3)

    logger.info("Change recipient to all users with email address")
    add_rule_page.set_recipient(index=0, recipient_option_name="All users with an email address")

    logger.info(
        "Skip stage '%s' and go to '%s'", STAGE_SENDING_CONDITIONS, STAGE_GENERAL_PROPERTIES
    )
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=4)
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=5)

    logger.info("Set rule description")
    add_rule_page.description_text_field.fill(expected_notification_subject)

    logger.info("Go to review settings and save")
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=6, is_last_stage=True)
    add_rule_page.save_and_test()

    logger.info("Disable the default notification rule")
    edit_rule_page = EditNotificationRule(dashboard_page.page, rule_position=0)
    edit_rule_page.check_disable_rule(True)
    edit_rule_page.save_and_test()

    try:
        was_filesystem_ruleset_created = False

        add_rule_filesystem_page = AddRuleFilesystems(dashboard_page.page)
        add_rule_filesystem_page.check_levels_for_user_free_space(True)
        add_rule_filesystem_page.description_text_field.fill(filesystem_rule_description)
        add_rule_filesystem_page.levels_for_used_free_space_warning_text_field.fill(used_space)
        add_rule_filesystem_page.save_button.click()
        add_rule_filesystem_page.activate_changes(test_site)

        was_filesystem_ruleset_created = True

        checkmk_agent = "Check_MK"
        service_search_page = ServiceSearchPage(dashboard_page.page)
        logger.info("Reschedule the '%s' service to trigger the notification", checkmk_agent)
        service_search_page.filter_sidebar.apply_filters(service_search_page.services_table)
        service_search_page.reschedule_check(host_name, checkmk_agent)
        service_search_page.wait_for_check_status_update(host_name, service_name, ServiceState.WARN)

        logger.info("Waiting for email %s from for user %s", username, email)
        email_manager.wait_for_email(expected_notification_subject)

    finally:
        logger.info("Delete the created rule")
        notification_configuration_page = NotificationConfiguration(dashboard_page.page)
        notification_configuration_page.delete_notification_rule(expected_notification_subject)

        logger.info("Enable the default notification rule")
        edit_notification_rule_page = EditNotificationRule(
            notification_configuration_page.page, rule_position=0
        )
        edit_notification_rule_page.check_disable_rule(False)
        edit_notification_rule_page.apply_and_create_another_rule()

        if was_filesystem_ruleset_created:
            filesystems_rules_page = Ruleset(
                dashboard_page.page,
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
