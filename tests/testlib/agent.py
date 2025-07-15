#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
This module provides a collection of utility functions and context managers for managing and testing
the Checkmk agent in various environments.
"""

import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, assert_never, Literal

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site
from tests.testlib.utils import (
    daemon,
    DaemonTerminationMode,
    execute,
    is_containerized,
    run,
)

from cmk.ccc.hostaddress import HostName

logger = logging.getLogger(__name__)

OMD_STATUS_CACHE = Path("/var/lib/check_mk_agent/cache/omd_status.cache")


def bake_agents(site: Site) -> None:
    expected_baking_start_time = time.time()
    bake_all_agents_response = site.openapi.post("domain-types/agent/actions/bake/invoke")
    bake_all_agents_response.raise_for_status()
    wait_for_baking_job(
        central_site=site,
        expected_start_time=expected_baking_start_time,
    )


def get_package_type() -> Literal["linux_deb", "linux_rpm"]:
    if os.path.exists("/var/lib/dpkg/status"):
        return "linux_deb"
    if (
        os.path.exists("/var/lib/rpm")
        and os.path.exists("/bin/rpm")
        or os.path.exists("/usr/bin/rpm")
    ):
        return "linux_rpm"
    raise NotImplementedError(
        "package_type recognition for the current environment is not supported yet. Please"
        " implement it if needed"
    )


def install_agent_package(package_path: Path) -> Path:
    package_type = get_package_type()
    installed_ctl_path = Path("/usr/bin/cmk-agent-ctl")
    if package_type == "linux_deb":
        agent_install_cmd = ["dpkg", "-i", package_path.as_posix()]
    elif package_type == "linux_rpm":
        agent_install_cmd = [
            "rpm",
            "-vU",
            "--oldpackage",
            "--replacepkgs",
            package_path.as_posix(),
        ]
    else:
        raise NotImplementedError(
            f"Installation of package type {package_type} is not supported yet, please implement it"
        )
    logger.info("Installing Checkmk agent...")
    try:
        agent_installation = run(agent_install_cmd, sudo=True)
        logger.info(
            "Agent installation output: %s\n%s",
            agent_installation.stdout,
            agent_installation.stderr,
        )
        assert installed_ctl_path.exists(), (
            f'Agent installation completed but agent controller not found at "{installed_ctl_path}"'
        )
        return installed_ctl_path
    except RuntimeError as e:
        process_table = run(["ps", "aux"]).stdout
        raise RuntimeError(f"Agent installation failed. Process table:\n{process_table}") from e


def uninstall_agent_package(package_name: str = "check-mk-agent") -> None:
    match package_type := get_package_type():
        case "linux_deb":
            run(
                ["dpkg", "--remove", package_name],
                sudo=True,
            )
        case "linux_rpm":
            run(
                ["rpm", "--erase", package_name],
                sudo=True,
            )
        case _:
            assert_never(package_type)


def download_and_install_agent_package(site: Site, tmp_dir: Path) -> Path:
    # Some smoke test to ensure the cmk-agent-ctl is executable in the current environment before
    # trying to install and use it in the following steps.
    # Please note: We can not verify the agent controller from the package below, as it is
    # automatically deleted by the post install script in case it is not executable (see also
    # agents/scripts/super-server/0_systemd/setup).
    run([site.path("share/check_mk/agents/linux/cmk-agent-ctl").as_posix(), "--version"])

    if site.edition.is_raw_edition():
        agent_download_resp = site.openapi.get(
            "domain-types/agent/actions/download/invoke",
            params={
                "os_type": get_package_type(),
            },
            headers={"Accept": "application/octet-stream"},
        )
    else:
        agent_download_resp = site.openapi.get(
            "domain-types/agent/actions/download_by_host/invoke",
            params={
                "agent_type": "generic",
                "os_type": get_package_type(),
            },
            headers={"Accept": "application/octet-stream"},
        )
    assert agent_download_resp.ok

    path_agent_package = tmp_dir / ("agent." + get_package_type())
    with path_agent_package.open(mode="wb") as tmp_agent_package:
        for chunk in agent_download_resp.iter_content(chunk_size=None):
            tmp_agent_package.write(chunk)

    return install_agent_package(path_agent_package)


@contextlib.contextmanager
def agent_controller_daemon(ctl_path: Path) -> Iterator[subprocess.Popen | None]:
    """Manually take over systemds job if we are in a container (where we have no systemd)."""
    if not is_containerized():
        yield None
        return

    logger.info("Running agent controller daemon...")
    with daemon(
        [
            sys.executable,
            "-B",
            str(repo_path() / "tests" / "scripts" / "agent_controller_daemon.py"),
            "--agent-controller-path",
            ctl_path.as_posix(),
        ],
        name_for_logging="agent controller",
        termination_mode=DaemonTerminationMode.GROUP,
        sudo=True,
    ) as agent_ctl_daemon:
        # wait for a dump being returned successfully, which may not work immediately
        # after starting the agent controller, so we retry for some time
        wait_until(
            lambda: execute(
                [ctl_path.as_posix(), "dump"],
                sudo=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).wait()
            == 0,
            timeout=30,
            interval=0.1,
        )
        yield agent_ctl_daemon


def register_controller(
    ctl_path: Path, site: Site, hostname: HostName, site_address: str | None = None
) -> None:
    # Register the agent controller with the site
    # (previously ran delete-all. Now part of _clean_agent_controller)
    run(
        [
            ctl_path.as_posix(),
            "--verbose",
            "register",
            "--server",
            site_address if site_address else site.http_address,
            "--site",
            site.id,
            "--hostname",
            hostname,
            "--user",
            "cmkadmin",
            "--password",
            site.admin_password,
            "--trust-cert",
        ],
        sudo=True,
    )


def wait_until_host_receives_data(
    site: Site,
    hostname: HostName,
    *,
    timeout: int = 120,
    interval: int = 20,
) -> None:
    try:
        wait_until(
            lambda: not site.execute(
                ["cmk", "-d", hostname],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).wait(),
            timeout=timeout,
            interval=interval,
        )
    except TimeoutError as e:
        try:
            _ = site.run(["cmk", "-d", hostname])
        except subprocess.CalledProcessError as excp:
            raise excp from e


def controller_status_json(controller_path: Path) -> Mapping[str, Any]:
    return json.loads(run([controller_path.as_posix(), "status", "--json"], sudo=True).stdout)


def controller_connection_json(
    controller_status: Mapping[str, Any], site: Site
) -> Mapping[str, Any]:
    """Get the site-specific connection details from a controller_status mapping.

    Assert that the connection is found and that the structure of the connection status is valid.
    """
    assert "connections" in controller_status, (
        f"No connections returned as part of controller status!\nStatus:\n{controller_status}"
    )
    # iterate over the connections and return the first match
    # return an empty response if no match was found (or the list is empty)
    controller_connection: Mapping[str, Any] = next(
        (
            _
            for _ in controller_status["connections"]
            if _["site_id"] == f"{site.http_address}/{site.id}"
        ),
        {},
    )
    assert controller_connection, (
        f'No controller connection found for site "{site.id}"!\nStatus:\n{controller_status}'
    )
    assert "remote" in controller_connection, (
        "No remote endpoint details returned as part of controller connection details!"
        f"\nStatus:\n{controller_status}"
    )
    assert "error" not in controller_connection["remote"], (
        f"Error in status output: {controller_connection['remote']['error']}"
    )
    assert "hostname" in controller_connection["remote"], (
        "No remote endpoint hostname returned as part of controller connection details!"
        f"\nStatus:\n{controller_status}"
    )
    assert "connection_mode" in controller_connection["remote"], (
        "No remote endpoint connection mode returned as part of controller connection details!"
        f"\nStatus:\n{controller_status}"
    )
    return controller_connection


def wait_until_host_has_services(
    site: Site,
    hostname: HostName,
    *,
    n_services_min: int = 5,
    timeout: int = 120,
    interval: int = 20,
) -> None:
    wait_until(
        lambda: _query_hosts_service_count(site, hostname) > n_services_min,
        timeout=timeout,
        interval=interval,
    )


def _query_hosts_service_count(site: Site, hostname: HostName) -> int:
    return (
        len(services_response.json()["value"])
        # the host might not yet exist at the point where we start waiting
        if (
            services_response := site.openapi.get(f"objects/host/{hostname}/collections/services")
        ).ok
        else 0
    )


def wait_for_baking_job(central_site: Site, expected_start_time: float) -> None:
    """Waits for the baking job to first start, then finish

    Args:
        central_site (Site): active site to use/watch
        expected_start_time (float): Time (as of time.time) when the job is expected to have started

    Raises:
        AssertionError: If the baking job didn't start after expected_start_time
            or didn't finish successfully after a certain amount of time.
    """
    waiting_time = 2
    waiting_cycles = 30
    for _ in range(waiting_cycles):
        time.sleep(waiting_time)
        baking_status = central_site.openapi.agents.get_baking_status()
        assert baking_status.state in (
            "initialized",
            "running",
            "finished",
        ), f"Unexpected baking state: {baking_status}"
        assert baking_status.started >= expected_start_time, (
            f"No baking job started after expected starting time: {expected_start_time}"
        )
        if baking_status.state == "finished":
            return
    raise AssertionError(
        f"Now waiting {waiting_cycles * waiting_time} seconds for baking job to finish, giving up..."
    )


def _remove_omd_status_cache() -> None:
    logger.info("Removing omd status agent cache...")
    try:
        run(["rm", "-f", str(OMD_STATUS_CACHE)], sudo=True)
    except subprocess.CalledProcessError as excp:
        excp.add_note("Failed to remove agent cache!")
        raise excp


def _all_omd_services_running_from_cache(site: Site) -> tuple[bool, str]:
    omd_status_cache_content = site.read_file(OMD_STATUS_CACHE)
    assert f"[{site.id}]" in omd_status_cache_content, (
        f'Site "{site.id}" not found in "{OMD_STATUS_CACHE}"!'
    )
    assert "OVERALL" in omd_status_cache_content

    # extract text between '[<site.id>]' and 'OVERALL'
    match_extraction = re.findall(rf"\[{site.id}\]([^\\]*?)OVERALL", omd_status_cache_content)
    sub_stdout = match_extraction[0] if match_extraction else ""

    # find all occurrences of one or more digits in the extracted stdout
    match_assertion = re.findall(r"\d+", sub_stdout)
    return all(int(match) == 0 for match in match_assertion), omd_status_cache_content


def wait_for_agent_cache_omd_status(site: Site, max_count: int = 20, waiting_time: int = 5) -> None:
    """Force re-generation of the omd status agent cache until it matches the current omd status."""
    count = 0

    while site.is_running() and count < max_count:
        if OMD_STATUS_CACHE.exists():
            fully_running, cache_content = _all_omd_services_running_from_cache(site)
            if fully_running:
                logger.info("Agent cache reports site to be fully running")
                return
            logger.info(
                "Agent cache reports site NOT to be fully running. Agent cache content:\n%s",
                cache_content,
            )
            # to force agent cache regeneration we remove the cache file
            _remove_omd_status_cache()

        logger.info("Waiting for agent cache to be generated...")
        time.sleep(waiting_time)
        count += 1

    logger.info("Agent cache not matching the current OMD status")


@contextlib.contextmanager
def clean_up_host(site: Site, hostname: HostName) -> Iterator[None]:
    try:
        yield
    finally:
        deleted = False
        if site.openapi.hosts.get(hostname):
            logger.info("Delete created host %s", hostname)
            site.openapi.hosts.delete(hostname)
            deleted = True

        if deleted:
            site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
