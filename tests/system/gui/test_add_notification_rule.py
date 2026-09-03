#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

import pytest

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.setup.notification_configuration import (
    NotificationConfiguration,
)
from tests.system.gui.testlib.playwright.pom.setup.notification_rules import (
    AddNotificationRule,
    EditNotificationRule,
    STAGE_FILTER_HOSTS_SERVICES,
    STAGE_GENERAL_PROPERTIES,
    STAGE_NOTIFICATION_METHOD,
    STAGE_RECIPIENT,
    STAGE_SENDING_CONDITIONS,
    STAGE_TRIGGERING_EVENTS,
)
from tests.testlib.emails import EmailManager
from tests.testlib.notifications import NotificationTarget
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="This test is flaky, investigation is required. See CMK-32258")
@pytest.mark.usefixtures("notification_user")
def test_add_new_notification_rule(
    dashboard_page: MainDashboard,
    notification_host: NotificationTarget,
    notification_user: tuple[str, str],
    email_manager: EmailManager,
    test_site: Site,
    tmp_path: Path,
) -> None:
    """Test adding a new notification rule creates the expected email"""
    email_manager.temp_folder = tmp_path
    username, email = notification_user
    host_name = notification_host.host_name
    service_name = notification_host.service_name
    expected_notification_subject = "GUI E2E Test Add Notification Rule"

    logger.info("Add new notification rule")

    add_rule_page = AddNotificationRule(dashboard_page.page)

    logger.info("Ensure Guided Mode")
    add_rule_page.ensure_guided_mode()

    logger.info(
        "Skip stage '%s' and go to '%s'", STAGE_TRIGGERING_EVENTS, STAGE_FILTER_HOSTS_SERVICES
    )
    add_rule_page.validate_button_text_and_goto_next_qs_stage(current_stage=1)

    logger.info("Set Hosts on Host filters to '%s'", host_name)
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
        logger.info("Set '%s' to WARN to trigger the notification", service_name)
        test_site.send_service_check_result(
            host_name, service_name, 1, "FAKE WARN", expected_state=1
        )

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
        edit_notification_rule_page.apply()

        email_manager.clean_emails(expected_notification_subject)
