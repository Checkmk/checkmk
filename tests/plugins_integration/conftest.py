# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Generator

import pytest

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name

LOGGER = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--update-checks",
        action="store_true",
        default=False,
        help="Store checks-output files to be used as static references",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "update_checks: run test marked as update_checks")


def pytest_collection_modifyitems(config, items):
    skip_update_checks = pytest.mark.skip(
        reason="Test used to store checks output. Selectable with --update-checks"
    )
    skip_check_tests = pytest.mark.skip(
        reason="Only tests marked as 'update_checks' have been selected"
    )
    for item in items:
        if ("update_checks" in item.keywords) == config.getoption("--update-checks"):
            continue
        item.add_marker(
            skip_update_checks if "update_checks" in item.keywords else skip_check_tests
        )


@pytest.fixture(name="test_site", scope="session")
def site() -> Iterator[Site]:
    LOGGER.info("Setting up testsite")
    reuse = os.environ.get("REUSE")
    # if REUSE is undefined, a site will neither be reused nor be dropped
    reuse_site = reuse == "1"
    drop_site = reuse == "0"
    sf = get_site_factory(
        prefix="plugins_",
        fallback_branch=current_base_branch_name,
    )

    site_to_return = sf.get_existing_site("central")
    if site_to_return.exists() and reuse_site:
        LOGGER.info("Reuse existing site (REUSE=1)")
    else:
        if site_to_return.exists() and drop_site:
            LOGGER.info("Dropping existing site (REUSE=0)")
            site_to_return.rm()
        LOGGER.info("Creating new site")
        site_to_return = sf.get_site("central")
    LOGGER.info("Testsite %s is up", site_to_return.id)

    try:
        yield site_to_return
    finally:
        # teardown: saving results
        site_to_return.save_results()


@pytest.fixture(scope="session")
def setup(test_site: Site) -> Generator:
    """Setup test-site and perform cleanup after test execution."""

    omd_root = Path(test_site.root)
    folders = [
        f"{omd_root}/etc/check_mk/conf.d/wato/agents",
        f"{omd_root}/var/check_mk/agent_output",
    ]

    # create wato-agents and agent-output folders in the test site
    for folder in folders:
        LOGGER.info('Creating folder "%s"...', folder)
        assert test_site.execute(["mkdir", "-p", folder]).wait() == 0

    # create wato-hosts by injecting the corresponding python script in the test site
    injected_script = Path(__file__).parent.resolve() / "injected_scripts/wato_hosts.py"
    wato_hosts_path = omd_root / "etc/check_mk/conf.d/wato/agents/hosts.mk"

    LOGGER.info("Creating hosts in wato...")
    assert run_as_superuser(["cp", str(injected_script), str(wato_hosts_path)]).returncode == 0

    # create wato-rules by injecting the corresponding python script in the test site
    injected_script = Path(__file__).parent.resolve() / "injected_scripts/wato_rules.py"
    wato_rules_path = omd_root / "etc/check_mk/conf.d/wato/agents/rules.mk"

    LOGGER.info("Creating rules in wato...")
    assert run_as_superuser(["cp", str(injected_script), str(wato_rules_path)]).returncode == 0

    # inject agent-output in the test site
    injected_output = Path(__file__).parent.resolve() / "agent_output"
    agent_output_path = omd_root / "var/check_mk/"

    LOGGER.info("Injecting agent-output...")
    assert (
        run_as_superuser(["cp", "-r", str(injected_output), str(agent_output_path)]).returncode == 0
    )

    yield

    # cleanup existing wato-agents and agent-output folders in the test site
    for folder in folders:
        LOGGER.info('Removing folder "%s"...', folder)
        assert test_site.execute(["rm", "-rf", folder]).wait() == 0


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    LOGGER.info("Executing: %s", subprocess.list2cmdline(cmd))
    completed_process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        check=False,
    )
    return completed_process


def run_as_superuser(cmd: list[str]) -> subprocess.CompletedProcess:
    cmd = ["/usr/bin/sudo"] + cmd
    return run_cmd(cmd)
