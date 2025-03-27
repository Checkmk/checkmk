#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.cloud_quick_setups import (
    AWSAddNewConfiguration,
    AWSConfigurationList,
    QuickSetupMultiChoice,
)
from tests.gui_e2e.testlib.playwright.pom.setup.hosts import SetupHost
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset
from tests.testlib.common.utils import run
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="fake_aws_dump", scope="module")
def fixture_fake_aws_dump(test_site: Site) -> Iterator[None]:
    """Fake the AWS special agent used within Checkmk site.

    Quick setup performs validation of AWS connection.
    Faking the AWS agent bypasses such validations, which are 'out-of-scope' of UI tests.
    """
    fake_agent_aws = Path(__file__).parent / "fake_agent_aws.py"
    aws_agent = test_site.root / "lib" / "check_mk" / "special_agents" / "agent_aws.py"
    backup_agent = str(aws_agent).replace(".py", ".py.bck")
    run(["cp", str(aws_agent), backup_agent], sudo=True)
    fake_aws_process = run(["cp", str(fake_agent_aws), str(aws_agent)], sudo=True)
    yield
    if fake_aws_process.returncode == 0 and os.getenv("CLEANUP", "1") == "1":
        run(["cp", str(backup_agent), str(aws_agent)], sudo=True)
        run(["rm", str(backup_agent)], sudo=True)


@pytest.fixture(name="aws_qs_config_page")
def fixture_aws_qs_config_page(
    fake_aws_dump: None, dashboard_page: Dashboard
) -> Iterator[AWSAddNewConfiguration]:
    """Navigate to the AWS Quick setup page and add new configuration page"""
    configuration_name = "my_aws_account"
    folder_details = AWSAddNewConfiguration.FolderDetails(
        name="aws_folder",
        parent="Main",
        create_new=True,
    )
    aws_qs_config_page = AWSAddNewConfiguration(
        dashboard_page.page,
        configuration_name=configuration_name,
        folder_details=folder_details,
    )
    yield aws_qs_config_page
    aws_config_list_page = AWSConfigurationList(aws_qs_config_page.page)
    activate = False
    # quick check; validation is performed in the test
    if aws_config_list_page.configuration_row(configuration_name).count() > 0:
        aws_config_list_page.delete_configuration(configuration_name)
        activate = True

    list_hosts_page = SetupHost(aws_config_list_page.page)
    # the quick setup could have failed before the folder gets created
    if list_hosts_page.folder_icon(folder_details.name).count() > 0:
        list_hosts_page.delete_folder(folder_details.name)
        activate = True

    if activate:  # only activate if we deleted the quick setup or folder
        list_hosts_page.activate_changes()


def test_minimal_configuration(aws_qs_config_page: AWSAddNewConfiguration, test_site: Site) -> None:
    """Validate setup of an AWS configuration using 'Quick setup: AWS'"""
    config_name = aws_qs_config_page.configuration_name
    host_name = "aws_host"

    aws_qs_config_page.specify_stage_one_details(
        access_key="my_aws_access_key",
        access_password="my_aws_access_password",
    )
    aws_qs_config_page.button_proceed_from_stage_one.click()
    expect(aws_qs_config_page.button_proceed_from_stage_two).to_be_enabled()
    expect(aws_qs_config_page.button_proceed_from_stage_one).not_to_be_visible()

    aws_qs_config_page.specify_stage_two_details(
        host_name,
        regions_to_monitor=["ap-south-1", "eu-central-1"],
        site_name=test_site.id,
    )
    aws_qs_config_page.button_proceed_from_stage_two.click()
    expect(aws_qs_config_page.button_proceed_from_stage_three).to_be_enabled()
    expect(aws_qs_config_page.button_proceed_from_stage_two).not_to_be_visible()

    aws_qs_config_page.specify_stage_three_details(
        services_per_region=QuickSetupMultiChoice([], ["Elastic Compute Cloud"]),
        global_services=QuickSetupMultiChoice(["Costs and usage"], []),
    )
    aws_qs_config_page.button_proceed_from_stage_three.click()
    expect(aws_qs_config_page.button_proceed_from_stage_four).to_be_enabled()
    expect(aws_qs_config_page.button_proceed_from_stage_three).not_to_be_visible()

    aws_qs_config_page.button_proceed_from_stage_four.click()
    # TODO: change to new text once available
    expect(
        aws_qs_config_page.main_area.locator().get_by_text("AWS services found!")
    ).to_be_visible()
    aws_qs_config_page.save_quick_setup()

    logger.info("Validate AWS configuration is listed.")
    qs_list_page = aws_qs_config_page.list_configuration_page()
    expect(qs_list_page.configuration_row(config_name)).to_be_visible()

    logger.info("Validate AWS folder and host is setup.")
    list_hosts_page = SetupHost(qs_list_page.page)
    list_hosts_page.click_and_wait(
        list_hosts_page.get_link(aws_qs_config_page.folder_details.name),
        expected_locator=list_hosts_page.get_link(host_name),
    )

    logger.info("Validate AWS rule is setup.")
    list_aws_rules_page = Ruleset(
        list_hosts_page.page, "Amazon Web Services (AWS)", "VM, cloud, container", exact_rule=True
    )
    expect(list_aws_rules_page.rule_source(rule_id=0)).to_have_text(re.compile(config_name))
    expect(list_aws_rules_page.get_link(config_name, exact=False)).to_be_visible()
