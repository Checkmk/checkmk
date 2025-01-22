#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from contextlib import contextmanager, nullcontext
from typing import Iterator

import pytest
from playwright.sync_api import expect

from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.repo import repo_path
from tests.testlib.site import Site
from tests.testlib.utils import makedirs

logger = logging.getLogger(__name__)


def _goto_setup_page(pw: LoginPage, setup_page: str) -> None:
    pw.click_and_wait(pw.main_menu.setup_menu(setup_page), navigate=True)
    pw.main_area.page.wait_for_load_state("load")
    pw.main_area.check_page_title(setup_page)


@contextmanager
def _write_rules_to_disk(site: Site) -> Iterator[None]:
    """Dump the rules for the rules migration part of the update test"""
    created_rules = {
        str(ruleset.get("id", "")): site.openapi.get_rules(ruleset.get("id", ""))
        for ruleset in site.openapi.get_rulesets()
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
    with open(tasks_file_path, "r", encoding="UTF-8") as tasks_file:
        logger.info('Importing tasks file "%s"...', tasks_file_path)
        tasks: dict[str, list[dict[str, str]]] = json.load(tasks_file)
    return tasks


def _create_rule(rule_name: str, pw: LoginPage, tasks: dict[str, list[dict[str, str]]]) -> None:
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


def _create_rules(pw: LoginPage) -> dict[str, list[str]]:
    rules_pages = ["Host monitoring rules"]
    tasks = _get_tasks()
    created_rules = {}
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


def test_create_rules(
    test_site: Site, logged_in_page: LoginPage, pytestconfig: pytest.Config
) -> None:
    with (
        _write_rules_to_disk(test_site)
        if pytestconfig.getoption("--update-rules")
        else nullcontext()
    ):
        # set up a host group
        host_group_name = "test-rules"
        test_site.openapi.create_host_group(host_group_name, host_group_name)

        # set up "Custom icons and actions"
        logged_in_page.main_menu.setup_searchbar.fill("Custom icons and actions")
        logged_in_page.click_and_wait(
            logged_in_page.main_menu.locator().get_by_role(
                role="link", name="Custom icons and actions"
            ),
            navigate=True,
        )
        logged_in_page.main_area.locator().get_by_role(
            role="button", name="Add new element"
        ).click()

        # Locator corresponding to (added) elements for 'current settings'.
        current_setting = (
            logged_in_page.main_area.locator()
            .get_by_role("row")
            .filter(has=logged_in_page.main_area.locator().get_by_title("Current setting"))
            .locator("td[class='content']")
        )

        current_setting.get_by_role("textbox").fill("test")
        current_setting.get_by_role("link", name="Choose another icon").click()
        current_setting.locator("a[class='icon']").get_by_title("2fa", exact=True).click()
        logged_in_page.click_and_wait(
            logged_in_page.main_area.get_suggestion("Save"), navigate=True
        )

        existing_rules = {
            ruleset_title: len(test_site.openapi.get_rules(ruleset.get("id", "")))
            for ruleset in test_site.openapi.get_rulesets()
            if (ruleset_title := ruleset.get("title"))
        }
        for ruleset_name, rule_count in existing_rules.items():
            logger.info('Existing rules for ruleset "%s": %s', ruleset_name, rule_count)

        logger.info("Create all rules...")
        created_rules = _create_rules(logged_in_page)
        for page, rule_names in created_rules.items():
            logger.info('Rules created for page "%s": %s', page, rule_names)

        logger.info("Activate all changes...")
        test_site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)

        logger.info("Verify all rules...")
        total_rules = {
            ruleset_title: len(test_site.openapi.get_rules(ruleset.get("id", "")))
            for ruleset in test_site.openapi.get_rulesets()
            if (ruleset_title := ruleset.get("title")) and ruleset_title in created_rules
        }
        for ruleset_name, rule_count in total_rules.items():
            logger.info('Total rules for ruleset "%s": %s', ruleset_name, rule_count)
            created_rule_count = rule_count - existing_rules.get(ruleset_name, 0)
            logger.info('Created rules for ruleset "%s": %s', ruleset_name, created_rule_count)
            assert (
                created_rule_count == 1
            ), f'Rule creation for ruleset "{ruleset_name}" has failed!'
