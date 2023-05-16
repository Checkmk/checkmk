# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

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


def _omd_root_path(site_id: str) -> Path:
    return Path(run_as_superuser(["su", "-l", f"{site_id}", "-c", "echo $OMD_ROOT"]).stdout.strip())


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


def run_as_site_user(site_name: str, cmd: list[str]) -> subprocess.CompletedProcess:
    cmd = ["/usr/bin/sudo", "-i", "-u", site_name] + cmd
    return run_cmd(cmd)


@dataclass
class SiteFolders:
    site_id: str
    folders = ["$OMD_ROOT/etc/check_mk/conf.d/wato/agents", "$OMD_ROOT/var/check_mk/agent_output"]

    def cleanup(self) -> "SiteFolders":
        """Cleanup existing wato-agents and agent-output folders in the test site."""
        for folder in self.folders:
            LOGGER.info('Removing folder "%s"...', folder)
            assert run_as_site_user(self.site_id, ["rm", "-rf", folder]).returncode == 0
        return self

    def create(self) -> "SiteFolders":
        """Create wato-agents and agent-output folders in the test site."""
        for folder in self.folders:
            LOGGER.info('Creating folder "%s"...', folder)
            assert run_as_site_user(self.site_id, ["mkdir", "-p", folder]).returncode == 0
        return self


def create_wato_hosts(site_id: str) -> None:
    """Create wato-hosts by injecting the corresponding python script in the test site."""
    omd_root = _omd_root_path(site_id)
    injected_script = Path(__file__).parent.resolve() / "injected_scripts/wato_hosts.py"
    wato_hosts_path = omd_root / "etc/check_mk/conf.d/wato/agents/hosts.mk"

    LOGGER.info("Creating hosts in wato...")
    assert run_as_superuser(["cp", str(injected_script), str(wato_hosts_path)]).returncode == 0


def create_wato_rules(site_id: str) -> None:
    """Create wato-rules by injecting the corresponding python script in the test site."""
    omd_root = _omd_root_path(site_id)
    injected_script = Path(__file__).parent.resolve() / "injected_scripts/wato_rules.py"
    wato_rules_path = omd_root / "etc/check_mk/conf.d/wato/agents/rules.mk"

    LOGGER.info("Creating rules in wato...")
    assert run_as_superuser(["cp", str(injected_script), str(wato_rules_path)]).returncode == 0


def inject_agent_output(site_id: str) -> None:
    """Inject agent-output in the test site."""
    omd_root = _omd_root_path(site_id)
    injected_output = Path(__file__).parent.resolve() / "agent_output"
    agent_output_path = omd_root / "var/check_mk/"

    LOGGER.info("Injecting agent-output...")
    assert (
        run_as_superuser(["cp", "-r", str(injected_output), str(agent_output_path)]).returncode == 0
    )
