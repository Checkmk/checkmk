#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name, repo_path
from tests.testlib.version import CMKVersion, version_from_env

from cmk.utils.hostaddress import HostName
from cmk.utils.version import Edition

from .conftest import get_site_status, update_site

logger = logging.getLogger(__name__)


@pytest.mark.cee
def test_update_rules(
    test_setup: tuple[Site, bool],
) -> None:
    test_site, disable_interactive_mode = test_setup
    base_version = test_site.version

    host_name = HostName("test-rules")
    host_group_name = "test-rules"

    logger.info("Creating new host: %s", host_name)
    test_site.openapi.create_host(
        hostname=host_name,
        folder="/",
        attributes={"ipaddress": "127.0.0.1", "tag_agent": "no-agent"},
        bake_agent=False,
    )
    logger.info("Creating new host group: %s", host_group_name)
    test_site.openapi.create_host_group(host_group_name, host_group_name)
    test_site.activate_changes_and_wait_for_core_reload()

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    test_site.activate_changes_and_wait_for_core_reload()

    rules_folder = repo_path() / "tests" / "update" / "rules"
    try:
        with open(rules_folder / "ignore.txt", "r", encoding="UTF-8") as ignore_list_file:
            ignore_list = [_ for _ in ignore_list_file.read().splitlines() if _]
    except FileNotFoundError:
        ignore_list = []
    rules_file_names = [
        _ for _ in os.listdir(rules_folder) if _.endswith(".json") and _ not in ignore_list
    ]
    for rules_file_name in rules_file_names:
        rules_file_path = rules_folder / rules_file_name
        with open(rules_file_path, "r", encoding="UTF-8") as ruleset_file:
            logger.info('Importing rules file "%s"...', rules_file_path)
            rules = json.load(ruleset_file)
            for rule in rules:
                test_site.openapi.create_rule(value=rule)
    test_site.activate_changes_and_wait_for_core_reload()

    target_site = update_site(test_site, target_version, not disable_interactive_mode)

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)
