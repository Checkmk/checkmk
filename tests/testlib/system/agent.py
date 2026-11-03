#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""
This module provides a collection of utility functions and context managers for managing and testing
the Checkmk agent in various environments.
"""

import contextlib
import json
import logging
import re
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping
from pathlib import Path, PurePath, PurePosixPath
from typing import Any, assert_never, Literal

from cmk.ccc.hostaddress import HostName
from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import (
    daemon,
    DaemonTerminationMode,
    execute,
    is_containerized,
    run,
    systemd_is_running,
)
from tests.testlib.system.host_under_test import HostUnderTest, LocalHost
from tests.testlib.system.site import Site
from tests.testlib.system.systemd import systemd_managed_agent_controller

logger = logging.getLogger(__name__)

OMD_STATUS_CACHE = Path("/var/lib/check_mk_agent/cache/omd_status.cache")
AGENT_CTL = PurePosixPath("/usr/bin/cmk-agent-ctl")

_LOCAL_HOST = LocalHost()


def bake_agents(site: Site) -> None:
    expected_baking_start_time = time.time()
    bake_all_agents_response = site.openapi.post("domain-types/agent/actions/bake/invoke")
    bake_all_agents_response.raise_for_status()
    wait_for_baking_job(
        central_site=site,
        expected_start_time=expected_baking_start_time,
    )


def get_package_type(host: HostUnderTest = _LOCAL_HOST) -> Literal["linux_deb", "linux_rpm"]:
    if host.run(["test", "-e", "/var/lib/dpkg/status"], check=False).returncode == 0:
        return "linux_deb"
    has_rpm = "test -e /usr/bin/rpm || { test -e /var/lib/rpm && test -e /bin/rpm; }"
    if host.run(["sh", "-c", has_rpm], check=False).returncode == 0:
        return "linux_rpm"
    raise NotImplementedError(
        "package_type recognition for the current environment is not supported yet. Please"
        " implement it if needed"
    )


def install_agent_package(package_path: Path, host: HostUnderTest = _LOCAL_HOST) -> Path:
    install_agent_package_with_output(package_path, host)
    return Path(AGENT_CTL)


def install_agent_package_with_output(
    package_path: Path, host: HostUnderTest = _LOCAL_HOST
) -> subprocess.CompletedProcess[str]:
    """Install an agent package on the host and hand back what the maintainer scripts printed.

    The maintainer scripts run without `set -e`, and the super server dispatcher runs its loop
    in a pipeline subshell, so a deployment that went wrong still exits zero. Callers that care
    have to look at the output.
    """
    package_dir = PurePosixPath("/tmp/cmk-agent-package")
    on_host = package_dir / package_path.name
    host.run(["mkdir", "-p", package_dir.as_posix()], sudo=True)
    host.copy_to(package_path, on_host)
    match package_type := get_package_type(host):
        case "linux_deb":
            agent_install_cmd = ["dpkg", "-i", on_host.as_posix()]
        case "linux_rpm":
            agent_install_cmd = ["rpm", "-vU", "--oldpackage", "--replacepkgs", on_host.as_posix()]
        case _:
            assert_never(package_type)

    logger.info("Installing Checkmk agent...")
    installation = host.run(agent_install_cmd, sudo=True, check=False)
    logger.info("Agent installation output: %s\n%s", installation.stdout, installation.stderr)
    if installation.returncode != 0:
        process_table = host.run(["ps", "aux"], check=False).stdout
        raise RuntimeError(
            f"Agent installation failed with exit code {installation.returncode}.\n"
            f"stdout:\n{installation.stdout}\nstderr:\n{installation.stderr}\n"
            f"Process table:\n{process_table}"
        )
    if host.run(["test", "-x", AGENT_CTL.as_posix()], check=False).returncode != 0:
        # agents/scripts/super-server/0_systemd/setup deletes a controller it cannot run.
        raise RuntimeError(
            f'Agent installation completed but agent controller not found at "{AGENT_CTL}"'
        )
    return installation


def uninstall_agent_package(
    package_name: str = "check-mk-agent", host: HostUnderTest = _LOCAL_HOST
) -> None:
    match package_type := get_package_type(host):
        case "linux_deb":
            host.run(["dpkg", "--remove", package_name], sudo=True)
        case "linux_rpm":
            host.run(["rpm", "--erase", package_name], sudo=True)
        case _:
            assert_never(package_type)


def purge_agent_package(
    package_name: str = "check-mk-agent", host: HostUnderTest = _LOCAL_HOST
) -> None:
    """Remove the package and its configuration files, if it is there at all.

    After a plain dpkg --remove, the next installation runs postinst as an upgrade from the
    version whose configuration files are left behind.
    """
    match package_type := get_package_type(host):
        case "linux_deb":
            host.run(["dpkg", "--purge", package_name], sudo=True)
        case "linux_rpm":
            if host.run(["rpm", "-q", package_name], check=False).returncode == 0:
                host.run(["rpm", "--erase", package_name], sudo=True)
        case _:
            assert_never(package_type)


def download_and_install_agent_package(site: Site, tmp_dir: Path) -> Path:
    # Some smoke test to ensure the cmk-agent-ctl is executable in the current environment before
    # trying to install and use it in the following steps.
    # Please note: We can not verify the agent controller from the package below, as it is
    # automatically deleted by the post install script in case it is not executable (see also
    # agents/scripts/super-server/0_systemd/setup).
    run([site.path("share/check_mk/agents/linux/cmk-agent-ctl").as_posix(), "--version"])
    return install_agent_package(download_agent_package(site, get_package_type(), tmp_dir))


def download_agent_package(
    site: Site, package_type: Literal["linux_deb", "linux_rpm"], target_dir: Path
) -> Path:
    """Download the generic agent package of the site.

    The Community edition serves the vanilla package. The other editions serve the baked one,
    so for them the caller has to run bake_agents() first.
    """
    if site.edition.is_community_edition():
        agent_download_resp = site.openapi.get(
            "domain-types/agent/actions/download/invoke",
            params={"os_type": package_type},
            headers={"Accept": "application/octet-stream"},
        )
    else:
        agent_download_resp = site.openapi.get(
            "domain-types/agent/actions/download_by_host/invoke",
            params={"agent_type": "generic", "os_type": package_type},
            headers={"Accept": "application/octet-stream"},
        )
    if not agent_download_resp.ok:
        raise RuntimeError(
            f"Agent download failed ({agent_download_resp.status_code}): {agent_download_resp.text}"
        )

    path_agent_package = target_dir / ("agent." + package_type)
    with path_agent_package.open(mode="wb") as tmp_agent_package:
        for chunk in agent_download_resp.iter_content(chunk_size=None):
            tmp_agent_package.write(chunk)
    return path_agent_package


@contextlib.contextmanager
def agent_controller_daemon(ctl_path: Path) -> Iterator[None]:
    """Make sure the agent controller and the agent socket are up for the duration.

    In a container with systemd both are units that the agent package enabled and started. In a
    container without systemd, tests/scripts/agent_controller_daemon.py takes their place. Both
    mechanisms delete all registrations of the controller, so outside a container nothing is
    done.
    """
    if not is_containerized():
        logger.warning(
            "Not in a container: nothing manages the agent controller, and registrations made "
            "by this test will not be cleaned up."
        )
        yield
    elif systemd_is_running():
        with systemd_managed_agent_controller(_LOCAL_HOST, ctl_path):
            yield
    else:
        with _shimmed_agent_controller(ctl_path):
            yield


@contextlib.contextmanager
def _shimmed_agent_controller(ctl_path: Path) -> Iterator[None]:
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
    ):
        # wait for a dump being returned successfully, which may not work immediately
        # after starting the agent controller, so we retry for some time
        wait_until(
            lambda: (
                execute(
                    [ctl_path.as_posix(), "dump"],
                    sudo=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).wait()
                == 0
            ),
            timeout=30,
            interval=0.1,
        )
        yield


def register_controller(
    ctl_path: PurePath,
    site: Site,
    hostname: HostName,
    site_address: str | None = None,
    host: HostUnderTest = _LOCAL_HOST,
) -> None:
    # Register the agent controller with the site
    # (previously ran delete-all. Now part of _clean_agent_controller)
    host.run(
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
            lambda: (
                not site.execute(
                    ["cmk", "-d", hostname],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).wait()
            ),
            timeout=timeout,
            interval=interval,
        )
    except TimeoutError as e:
        try:
            _ = site.run(["cmk", "-d", hostname])
        except subprocess.CalledProcessError as excp:
            raise excp from e


def controller_status_json(
    controller_path: PurePath, host: HostUnderTest = _LOCAL_HOST
) -> Mapping[str, Any]:
    json_data: Mapping[str, Any] = json.loads(
        host.run([controller_path.as_posix(), "status", "--json"], sudo=True).stdout
    )
    return json_data


def controller_connection_json(
    controller_status: Mapping[str, Any], site: Site
) -> Mapping[str, Any]:
    """Get the site-specific connection details from a controller_status mapping.

    Assert that the connection is found and that the structure of the connection status is valid.
    """
    if "connections" not in controller_status:
        raise AssertionError(
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
    if not controller_connection:
        raise AssertionError(
            f'No controller connection found for site "{site.id}"!\nStatus:\n{controller_status}'
        )
    if "remote" not in controller_connection:
        raise AssertionError(
            "No remote endpoint details returned as part of controller connection details!"
            f"\nStatus:\n{controller_status}"
        )
    if "error" in controller_connection["remote"]:
        raise AssertionError(f"Error in status output: {controller_connection['remote']['error']}")
    for key in ("hostname", "connection_mode"):
        if key not in controller_connection["remote"]:
            raise AssertionError(
                f"No remote endpoint {key.replace('_', ' ')} returned as part of controller "
                f"connection details!\nStatus:\n{controller_status}"
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
    try:
        wait_until(
            lambda: _query_hosts_service_count(site, hostname) > n_services_min,
            timeout=timeout,
            interval=interval,
        )
    except TimeoutError:
        logger.exception(
            "wait_until_host_has_services timed out for host %r on site %r. "
            "Dumping diagnostics:\n%s",
            hostname,
            site.id,
            _wait_for_services_diagnostics(site, hostname),
        )
        raise


def _query_hosts_service_count(site: Site, hostname: HostName) -> int:
    return (
        len(services_response.json()["value"])
        # the host might not yet exist at the point where we start waiting
        if (
            services_response := site.openapi.post(
                f"objects/host/{hostname}/collections/services", json={}
            )
        ).ok
        else 0
    )


def _wait_for_services_diagnostics(site: Site, hostname: HostName) -> str:
    """Collect diagnostics to explain why services never showed up on the host.

    The typical cause is the central site's core being unreachable (see
    CMK-34867), which the bare TimeoutError from `wait_until` does not
    surface. Dump enough state to tell apart "core dead" from "discovery
    never produced services" from "host not created yet".
    """
    parts: list[str] = []
    try:
        omd_status = site.omd("status")
        parts.append(f"omd status (rc={omd_status.returncode}):\n{omd_status.stdout}")
    except Exception as exc:
        parts.append(f"Could not run 'omd status': {exc!r}")
    try:
        host_response = site.openapi.get(f"objects/host_config/{hostname}")
        parts.append(
            f"GET host_config/{hostname} -> {host_response.status_code}: {host_response.text[:500]}"
        )
    except Exception as exc:
        parts.append(f"Could not read host_config: {exc!r}")
    try:
        services_response = site.openapi.get(f"objects/host/{hostname}/collections/services")
        parts.append(
            f"GET host/{hostname}/collections/services -> {services_response.status_code}: "
            f"{services_response.text[:500]}"
        )
    except Exception as exc:
        parts.append(f"Could not read monitoring services: {exc!r}")
    try:
        pending = site.openapi.changes.get_pending()
        parts.append(f"Pending changes ({len(pending)}): {pending}")
    except Exception as exc:
        parts.append(f"Could not list pending changes: {exc!r}")
    for log_rel_path, tail_lines in (("var/log/cmc.log", 30), ("var/log/web.log", 50)):
        try:
            log_lines = site.read_file(log_rel_path).splitlines()
            parts.append(
                f"Last {tail_lines} lines of {log_rel_path}:\n" + "\n".join(log_lines[-tail_lines:])
            )
        except Exception as exc:
            parts.append(f"Could not read {log_rel_path}: {exc!r}")
    return "\n\n".join(parts)


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
        if baking_status.state not in ("initialized", "running", "finished"):
            raise AssertionError(f"Unexpected baking state: {baking_status}")
        if baking_status.started < expected_start_time:
            raise AssertionError(
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
    if f"[{site.id}]" not in omd_status_cache_content:
        raise RuntimeError(f'Site "{site.id}" not found in "{OMD_STATUS_CACHE}"!')
    if "OVERALL" not in omd_status_cache_content:
        raise RuntimeError(f'No "OVERALL" line in "{OMD_STATUS_CACHE}"!')

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
