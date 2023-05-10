# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name

LOGGER = logging.getLogger(__name__)


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


def cleanup_folders(site_id: str) -> None:
    """Cleanup existing wato-agents and agent-output folders in the test site."""
    wato_agents_path = "$OMD_ROOT/etc/check_mk/conf.d/wato/agents"
    agent_output_path = "$OMD_ROOT/var/check_mk/agent_output"

    LOGGER.info("Cleaning up wato-agents folder...")
    assert run_as_site_user(site_id, ["rm", "-rf", wato_agents_path]).returncode == 0

    LOGGER.info("Cleaning up agent-output folder...")
    assert run_as_site_user(site_id, ["rm", "-rf", agent_output_path]).returncode == 0


def create_folders(site_id: str) -> None:
    """Create wato-agents and agent-output folders in the test site."""
    wato_agents_path = "$OMD_ROOT/etc/check_mk/conf.d/wato/agents"
    agent_output_path = "$OMD_ROOT/var/check_mk/agent_output"

    LOGGER.info("Creating wato-agents folder...")
    assert run_as_site_user(site_id, ["mkdir", wato_agents_path]).returncode == 0

    LOGGER.info("Creating agent-output folder...")
    assert run_as_site_user(site_id, ["mkdir", agent_output_path]).returncode == 0


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
