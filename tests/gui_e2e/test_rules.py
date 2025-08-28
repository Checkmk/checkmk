#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path

import pytest
from faker import Faker
from playwright.sync_api import expect

from tests.gui_e2e.testlib.api_helpers import LOCALHOST_IPV4
from tests.gui_e2e.testlib.host_details import HostDetails
from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.add_rule_cpu_load import AddRuleCPULoad
from tests.gui_e2e.testlib.playwright.pom.setup.add_rule_disk_io_levels import AddRuleDiskIOLevels
from tests.gui_e2e.testlib.playwright.pom.setup.add_rule_periodic_discovery import (
    AddRulePeriodicServiceDiscovery,
)
from tests.gui_e2e.testlib.playwright.pom.setup.cpu_load_value_levels import CPULoadValueLevels
from tests.gui_e2e.testlib.playwright.pom.setup.diskstat_value_levels import DiskstatValueLevels
from tests.gui_e2e.testlib.playwright.pom.setup.host_effective_parameters import (
    HostEffectiveParameters,
)
from tests.gui_e2e.testlib.playwright.pom.setup.predictive_level_helpers import (
    BoundLevels,
    LevelType,
    PredictionPeriod,
    PredictiveLevels,
    PredictiveLevelType,
    PredictiveLevelTypeShort,
)
from tests.gui_e2e.testlib.playwright.pom.setup.ruleset import Ruleset
from tests.testlib.common.repo import repo_path
from tests.testlib.site import Site
from tests.testlib.utils import is_cleanup_enabled, makedirs

logger = logging.getLogger(__name__)


def _goto_setup_page(pw: Dashboard, setup_page: str) -> None:
    pw.click_and_wait(pw.main_menu.setup_menu(setup_page), navigate=True)
    pw.main_area.page.wait_for_load_state("load")
    pw.main_area.check_page_title(setup_page)


@contextmanager
def _write_rules_to_disk(site: Site) -> Iterator[None]:
    """Dump the rules for the rules migration part of the update test"""
    created_rules = {
        str(ruleset.get("id", "")): site.openapi.rules.get_all(ruleset.get("id", ""))
        for ruleset in site.openapi.rulesets.get_all()
    }
    try:
        yield
    finally:
        # skip rulesets which can not be imported currently
        skip_rulesets = ["icon_image"]
        # remove irrelevant keys from rule dumps, which are not supported by the POST endpoint
        strip_keys = ["folder_index"]

        for ruleset_name, rules in created_rules.items():
            ruleset_shortname = ruleset_name.rsplit(":", 1)[-1]
            if ruleset_name in skip_rulesets:
                continue
            rules_filename = f"{ruleset_shortname}.json"
            rules_dirpath = repo_path() / "tests" / "update" / "rules"
            rules_filepath = rules_dirpath / f"{ruleset_shortname}.json"

            # reformat rules for dump
            export_rules = [{key: _[key] for key in _ if key not in strip_keys} for _ in rules]

            logger.info(
                'Writing rules for ruleset "%s" to "%s"...',
                ruleset_name,
                rules_filename,
            )
            makedirs(rules_dirpath.as_posix())
            with open(rules_filepath, "w", encoding="UTF-8") as rules_file:
                json.dump(export_rules, rules_file, indent=2)


def _get_tasks() -> dict[str, list[dict[str, str]]]:
    tasks_file_path = repo_path() / "tests" / "gui_e2e" / "customize_rules.json"
    with open(tasks_file_path, encoding="UTF-8") as tasks_file:
        logger.info('Importing tasks file "%s"...', tasks_file_path)
        tasks: dict[str, list[dict[str, str]]] = json.load(tasks_file)
    return tasks


def _create_rule(rule_name: str, pw: Dashboard, tasks: dict[str, list[dict[str, str]]]) -> None:
    logger.info('Creating rule "%s"...', rule_name)
    pw.click_and_wait(
        pw.main_area.locator(".rulesets").get_by_role("link").get_by_text(rule_name),
        navigate=True,
    )
    pw.click_and_wait(pw.main_area.get_suggestion("Add rule"), navigate=True)

    # customize rule with non-default properties
    if rule_name in tasks:
        for task in tasks[rule_name]:
            locator: str = task["locator"]
            action: str = task["action"]
            kwargs = {arg: val for arg, val in task.items() if arg not in ("locator", "action")}
            caller = getattr(pw.main_area.locator(locator), action)
            caller(**kwargs)

    pw.click_and_wait(pw.main_area.get_suggestion("Save"), navigate=True)

    expect(pw.main_area.locator("div.error")).not_to_be_attached()


def _create_rules(pw: Dashboard) -> dict[str, list[str]]:
    rules_pages = ["Host monitoring rules"]
    tasks = _get_tasks()
    created_rules: dict[str, list[str]] = {}
    for rules_page in rules_pages:
        _goto_setup_page(pw, rules_page)
        rule_names = [
            rule_name
            for link in pw.main_area.locator(".rulesets").get_by_role("link").all()
            if (rule_name := link.text_content())
        ]
        for rule_name in rule_names:
            _create_rule(rule_name, pw, tasks)
            _goto_setup_page(pw, rules_page)
        created_rules[rules_page] = rule_names

    return created_rules


@pytest.fixture(name="restore_site_state")
def fixture_restore_site_state(test_site: Site) -> Iterator[None]:
    """Backup site configuration and rules and restore them."""
    # set up a host group
    host_group_name = "test-rules"
    test_site.openapi.host_groups.create(host_group_name, host_group_name)
    if is_cleanup_enabled():
        with test_site.backup_and_restore_files(
            files=[
                Path("etc/check_mk/multisite.d/wato/global.mk"),
                Path("etc/check_mk/conf.d/wato/rules.mk"),
            ],
        ):
            yield
        test_site.openapi.host_groups.delete(host_group_name)
        test_site.openapi.changes.activate_and_wait_for_completion()
    else:
        yield


def test_create_rules(
    test_site: Site,
    dashboard_page: Dashboard,
    pytestconfig: pytest.Config,
    restore_site_state: None,
) -> None:
    with (
        _write_rules_to_disk(test_site)
        if pytestconfig.getoption("--update-rules")
        else nullcontext()
    ):
        # set up "Custom icons and actions"
        dashboard_page.main_menu.setup_searchbar.fill("Custom icons and actions")
        dashboard_page.click_and_wait(
            dashboard_page.main_menu.locator().get_by_role(
                role="link", name="Custom icons and actions"
            ),
            navigate=True,
        )
        dashboard_page.main_area.locator().get_by_role(
            role="button", name="Add new element"
        ).click()

        # Locator corresponding to (added) elements for 'current settings'.
        current_setting = (
            dashboard_page.main_area.locator()
            .get_by_role("row")
            .filter(has=dashboard_page.main_area.locator().get_by_title("Current setting"))
            .locator("td[class='content']")
        )

        current_setting.get_by_role("textbox").fill("test")
        current_setting.get_by_role("link", name="Choose another icon").click()
        current_setting.locator("a[class='icon']").get_by_title("2fa", exact=True).click()
        dashboard_page.click_and_wait(
            dashboard_page.main_area.get_suggestion("Save"), navigate=True
        )

        existing_rules = {
            ruleset_title: len(test_site.openapi.rules.get_all(ruleset.get("id", "")))
            for ruleset in test_site.openapi.rulesets.get_all()
            if (ruleset_title := ruleset.get("title"))
        }
        for ruleset_name, rule_count in existing_rules.items():
            logger.info('Existing rules for ruleset "%s": %s', ruleset_name, rule_count)

        logger.info("Create all rules...")
        try:
            created_rules = _create_rules(dashboard_page)
            for page, rule_names in created_rules.items():
                logger.info('Rules created for page "%s": %s', page, rule_names)
        finally:
            logger.info("Activate all changes...")
            test_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)

        logger.info("Verify all rules...")
        total_rules = {
            ruleset_title: len(test_site.openapi.rules.get_all(ruleset.get("id", "")))
            for ruleset in test_site.openapi.rulesets.get_all()
            if (ruleset_title := ruleset.get("title")) and ruleset_title in created_rules
        }
        for ruleset_name, rule_count in total_rules.items():
            logger.info('Total rules for ruleset "%s": %s', ruleset_name, rule_count)
            created_rule_count = rule_count - existing_rules.get(ruleset_name, 0)
            logger.info('Created rules for ruleset "%s": %s', ruleset_name, created_rule_count)
            assert created_rule_count == 1, (
                f'Rule creation for ruleset "{ruleset_name}" has failed!'
            )


@pytest.mark.parametrize(
    "created_host",
    [
        pytest.param(
            HostDetails(
                name=f"test_host_{Faker().first_name()}",
                ip=LOCALHOST_IPV4,
            )
        )
    ],
    indirect=["created_host"],
)
def test_periodic_service_discovery_rule(
    dashboard_page: Dashboard,
    created_host: HostDetails,
    test_site: Site,
) -> None:
    """Test the creation & prioritization of a new rule for periodic service discovery.

    Create a new rule for periodic service discovery, move it to the top, check that the new rule
    was moved successfully. Then navigate to the 'Effective parameters of <host>' page and check the
    presence of the new rule.
    """
    rule_description = "Test rule description"
    period_in_hours = "12"

    logger.info("Add a new rule for periodic service discovery")
    add_periodic_service_discovery_page = AddRulePeriodicServiceDiscovery(dashboard_page.page)
    add_periodic_service_discovery_page.description_text_field.fill(rule_description)
    add_periodic_service_discovery_page.hours_text_field.fill(period_in_hours)
    add_periodic_service_discovery_page.save_button.click()
    ruleset_page = Ruleset(
        add_periodic_service_discovery_page.page,
        "Periodic service discovery",
        navigate_to_page=False,
    )
    ruleset_page.main_area.check_success(ruleset_page.created_new_rule_message)
    expect(
        ruleset_page.rule_position(rule_description),
        message="Unexpected position of the new rule after creation.",
    ).to_have_text("1")

    logger.info("Move the new rule to the top")
    new_rule_move_icon = ruleset_page.move_icon(rule_description)
    new_rule_move_icon.drag_to(ruleset_page.rules_table_header())
    expect(
        ruleset_page.rule_position(rule_description),
        message="Unexpected position of the new rule after moving it to the top",
    ).to_have_text("0")
    ruleset_page.activate_changes(test_site)

    logger.info(
        "Check that the new rule is present in the 'Effective parameters of %s' page",
        created_host.name,
    )
    effective_parameters_page = HostEffectiveParameters(ruleset_page.page, created_host)
    effective_parameters_page.expand_section("Service discovery rules")
    assert (
        effective_parameters_page.service_discovery_period.inner_text()
        == f"{period_in_hours} hours"
    ), "Unexpected service discovery period after adding a new rule"

    logger.info("Delete the new rule")
    ruleset_page = Ruleset(effective_parameters_page.page, "Periodic service discovery")
    ruleset_page.delete_icon(rule_description).click()
    ruleset_page.delete_button.click()


@pytest.mark.parametrize(
    "created_host",
    [
        pytest.param(
            HostDetails(
                name=f"test_host_{Faker().first_name()}",
                ip=LOCALHOST_IPV4,
            )
        )
    ],
    indirect=["created_host"],
)
def test_use_default_periodic_service_discovery_rule(
    dashboard_page: Dashboard, created_host: HostDetails
) -> None:
    """Test the default 'Periodic service discovery' rule values for monitoring hosts.

    Check that the default 'Periodic service discovery' rule values are correctly shown in the
    'Effective parameters of <host name>' page.
    """
    logger.info("Collect the default 'Periodic service discovery' rule values")
    ruleset_page = Ruleset(
        dashboard_page.page,
        "Periodic service discovery",
    )
    rules_count = ruleset_page.rule_rows.count()
    assert rules_count == 1, "Unexpected number of rules in the table"
    default_rule_values = ruleset_page.rule_values(rule_id=0).all_inner_texts()

    logger.info(
        "Check that the same rule is present in the 'Effective parameters of %s' page",
        created_host.name,
    )
    effective_parameters_page = HostEffectiveParameters(ruleset_page.page, created_host)
    effective_parameters_page.expand_section("Service discovery rules")
    rule_values = effective_parameters_page.service_discovery_values.all_inner_texts()
    assert default_rule_values == rule_values, "Unexpected rule values"


def test_predictive_levels_with_default_values(dashboard_page: Dashboard, test_site: Site) -> None:
    """Test configuring predictive levels with default values with adding a new rule
    for 'Disk IO levels' page.
    """

    rule_description = "Predictive levels rule with default values"
    logger.info("Add a new rule for 'Disk IO levels' page")
    is_rule_added = False
    try:
        disk_io_levels_page = AddRuleDiskIOLevels(dashboard_page.page)
        disk_io_levels_page.description_text_field.fill(rule_description)
        metric = "Read throughput"
        levels = DiskstatValueLevels(
            page=disk_io_levels_page,
            checkbox_label=metric,
        )
        levels.enable_levels()
        levels.set_level_type(LevelType.PREDICTIVE_LEVELS)
        levels.set_predictive_level_type(PredictiveLevelTypeShort.RELATIVE)
        disk_io_levels_page.save_button.click()
        is_rule_added = True

        service_rules_page = Ruleset(
            dashboard_page.page, disk_io_levels_page.rule_name, navigate_to_page=False
        )
        service_rules_page.main_area.check_success(service_rules_page.created_new_rule_message)
        assert service_rules_page.rule_rows.count() == 1, "Unexpected number of rules in the table"
        rule_values = service_rules_page.rule_values(rule_id=0).all_inner_texts()[0]

        # Get default predictive levels for the metric
        exp_rule = PredictiveLevels(
            relative_level_type=PredictiveLevelTypeShort.RELATIVE,
            relative_bound=BoundLevels(warning=10, critical=20),
        )

        exp_vals = exp_rule.get_checked_values()
        exp_vals.append(metric)
        for val in exp_vals:
            assert val in rule_values, (
                f"Expected value '{val}' not found in rule values: {rule_values}"
            )

        disk_io_levels_page.activate_changes(test_site)
    finally:
        if is_rule_added:
            logger.info(
                "Navigate to the '%s' page and delete the created rule.",
                disk_io_levels_page.rule_name,
            )
            service_rules_page = Ruleset(
                dashboard_page.page,
                disk_io_levels_page.rule_name,
                disk_io_levels_page.section_name,
                exact_rule=True,
            )
            service_rules_page.delete_rule(rule_id=0)
            service_rules_page.activate_changes(test_site)


def test_predictive_levels_with_custom_values(dashboard_page: Dashboard, test_site: Site) -> None:
    """Test configuring predictive levels with custom values while adding a new rule
    for 'CPU Load (not utilization!)' page.
    """

    rule_description = "Predictive levels rule with custom values"
    logger.info("Add a new rule for 'CPU Load (not utilization!)' page")
    cpu_load_page = AddRuleCPULoad(dashboard_page.page)
    cpu_load_page.description_text_field.fill(rule_description)

    is_rule_added = False
    try:
        levels = CPULoadValueLevels(
            page=cpu_load_page,
            checkbox_label="Levels on CPU load: 1 minute average",
        )
        levels.enable_levels()

        # Configure predictive levels with desired options
        levels.configure_predictive_levels(
            period_text=PredictionPeriod.HOURLY,
            horizon_days=30,
        )
        levels.upper_bound_checkbox.click()
        upper_bound = BoundLevels(warning=3.0, critical=6.0)
        levels.configure_upper_bound_levels(
            level_type=PredictiveLevelType.ABSOLUTE,
            warning=upper_bound.warning,
            critical=upper_bound.critical,
        )

        levels.lower_bound_checkbox.click()
        lower_bound = BoundLevels(warning=12.0, critical=18.0)
        levels.configure_lower_bound_levels(
            level_type=PredictiveLevelType.RELATIVE,
            warning=lower_bound.warning,
            critical=lower_bound.critical,
        )

        levels.upper_bound_limit_checkbox.click()
        upper_bound_limit = BoundLevels(warning=0.7, critical=1.2)
        levels.configure_upper_bound_limits(
            warning=upper_bound_limit.warning, critical=upper_bound_limit.critical
        )

        cpu_load_page.save_button.click()
        is_rule_added = True

        service_rules_page = Ruleset(
            dashboard_page.page, cpu_load_page.rule_name, navigate_to_page=False
        )
        service_rules_page.main_area.check_success(service_rules_page.created_new_rule_message)
        assert service_rules_page.rule_rows.count() == 1, "Unexpected number of rules in the table"
        rule_values = service_rules_page.rule_values(rule_id=0).all_inner_texts()[0]

        exp_rule = PredictiveLevels(
            period=PredictionPeriod.HOURLY,
            horizon_days=30,
            upper_level_type=PredictiveLevelType.ABSOLUTE,
            upper_bound=BoundLevels(warning=upper_bound.warning, critical=upper_bound.critical),
            lower_level_type=PredictiveLevelType.RELATIVE,
            lower_bound=BoundLevels(warning=lower_bound.warning, critical=lower_bound.critical),
            upper_bound_limit=BoundLevels(
                warning=upper_bound_limit.warning, critical=upper_bound_limit.critical
            ),
        )
        exp_vals = exp_rule.get_checked_values()
        for val in exp_vals:
            assert val in rule_values, (
                f"Expected value '{val}' not found in rule values: {rule_values}"
            )

        cpu_load_page.activate_changes(test_site)
    finally:
        if is_rule_added:
            logger.info(
                "Navigate to the '%s' page and delete the created rule.",
                cpu_load_page.rule_name,
            )
            service_rules_page = Ruleset(
                dashboard_page.page,
                cpu_load_page.rule_name,
                cpu_load_page.section_name,
                exact_rule=True,
            )
            service_rules_page.delete_rule(rule_id=0)
            service_rules_page.activate_changes(test_site)
