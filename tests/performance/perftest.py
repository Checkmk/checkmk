#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""What every performance scenario needs, and nothing that belongs to one of them.

The scenarios themselves live beside the tests that measure them, one package each. What is
left here is the state they share - which sites are under test, how many rounds and objects the
command line asked for - and the handling every scenario repeats: creating and deleting hosts in
bulk, discovering their services, reaching the GUI as a logged-in browser would, and putting up
the distributed environments a scenario is measured in (piggyback hub across the sites, or a
cluster of mocked remotes).

A scenario takes this object as its first argument rather than hanging off it as a method, so
adding one does not mean growing a class that every other scenario also imports.
"""

import json
import logging
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager, ExitStack
from pathlib import Path
from time import sleep, time
from urllib.parse import urljoin

import pytest
import requests
from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import BrowserContext, Page
from requests.auth import HTTPBasicAuth

from tests.performance.mock_remote_sites import mock_remote_site_cluster
from tests.testlib.site import ADMIN_USER as site_admin_user
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


class PerformanceTest:
    def __init__(
        self, central_site: Site, remote_sites: list[Site] | None, pytestconfig: pytest.Config
    ) -> None:
        """Initialize the performance test with a central site and a list of remote sites."""
        super().__init__()
        self.central_site = central_site
        self.remote_sites = remote_sites or []

        #: Host that pages needing a real one are pointed at. Overwritten by the fixture
        #: that creates it and discovers its services; the placeholder keeps URL
        #: substitution total for every page that does not care.
        self.monitored_host = "dummy"

        self.rounds = val if isinstance((val := pytestconfig.getoption("rounds")), int) else 16
        self.warmup_rounds = (
            val if isinstance((val := pytestconfig.getoption("warmup_rounds")), int) else 0
        )
        self.iterations = (
            val if isinstance((val := pytestconfig.getoption("iterations")), int) else 1
        )
        self.object_count = (
            val if isinstance((val := pytestconfig.getoption("object_count")), int) else 100
        )
        self.dcd_piggyback_rule_id = ""
        self.mocked_sites = (
            val
            if isinstance((val := pytestconfig.getoption("mocked_sites", default=None)), int)
            else 30
        )
        # Total piggybacked host count for distributed piggyback scenarios
        # (default: 2 * object_count, matching the real-remote-site variant).
        self.pb_hosts = (
            val
            if isinstance((val := pytestconfig.getoption("pb_hosts", default=None)), int)
            else 2 * self.object_count
        )
        # When set, bulk change activation hosts are spread over these site IDs
        # (used with mocked remote sites) instead of self.sites.
        self.bulk_change_target_site_ids: list[str] | None = None

    @property
    def sites(self) -> list[Site]:
        """Return a list of all sites used for the test."""
        return [self.central_site] + self.remote_sites

    @staticmethod
    def hostnames(hosts: list[dict[str, object]]) -> list[str]:
        """Return hostnames for a list of host dictionaries."""
        return [str(host["host_name" if "host_name" in host else "id"]) for host in hosts]

    @staticmethod
    def create_hosts(site: Site, hosts: list[dict[str, object]]) -> list[str]:
        """Create hosts using a list of host dictionaries."""
        hosts_created = site.openapi.hosts.bulk_create(
            hosts, bake_agent=False, ignore_existing=True
        )
        site.openapi.changes.activate_and_wait_for_completion()
        return PerformanceTest.hostnames(hosts_created)

    @staticmethod
    def delete_hosts(site: Site, hostnames: list[str]) -> None:
        """Delete hosts for all given host names."""
        if len(hostnames) == 0:
            return

        logger.info("Bulk-deleting %s hosts...", len(hostnames))
        site.openapi.hosts.bulk_delete(hostnames)
        site.openapi.changes.activate_and_wait_for_completion()

    @staticmethod
    def discover_services(site: Site, hostnames: list[str]) -> None:
        """Do a service bulk discovery for all given host names."""
        logger.info("Running service discovery...")
        site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion(
            hostnames, bulk_size=10
        )
        site.openapi.changes.activate_and_wait_for_completion()

    @staticmethod
    def login(site: Site, auth: HTTPBasicAuth) -> SetCookieParam:
        """Login to the Checkmk web UI and generate an auth cookie.

        Args:
            site: The target site.
            auth: An HTTPBasicAuth tuple with the username and password.

        Returns:
            SetCookieParam: The auth cookie for the login session.
        """
        login_url = urljoin(site.url, "login.py")
        session = requests.session()
        session.get(login_url, auth=auth)
        try:
            auth_cookie = next(
                cookie for cookie in session.cookies if cookie.name == f"auth_{site.id}"
            )
            return {
                "name": auth_cookie.name,
                "value": auth_cookie.value or "",
                "domain": auth_cookie.domain,
                "path": auth_cookie.path,
                "secure": auth_cookie.secure,
                "sameSite": "Lax",
            }
        except StopIteration as excp:
            excp.add_note(f'Failed to login to site "{site.id}"!')
            raise excp

    @staticmethod
    def page(site: Site, context: BrowserContext, login_as_admin: bool = True) -> Page:
        """Return a Playwright page object for a Checkmk web UI.

        Args:
            site: The target site.
            context: The Playwright BrowserContext object.
            login_as_admin: Specifies if the default admin user should be logged in.
        """
        if login_as_admin:
            auth = HTTPBasicAuth(site_admin_user, site.admin_password)
            auth_cookie = PerformanceTest.login(site, auth)
            context.add_cookies([auth_cookie])

        return context.new_page()

    @staticmethod
    def auto_increment_filename(
        path: Path,
        listdir: Callable[[str | Path | None], list[str]] = os.listdir,
    ) -> Path:
        """Return a path with an auto-incremented numeric suffix.

        Scans the target directory for files matching "{stem}.{n}{suffix}", picks the
        next available integer, and returns the corresponding Path. Uses the provided
        listdir callable for testability.

        Args:
            path: The path to add the auto-incremented number to.
            listdir: An optional alternative callable to list a directory.
        """
        directory = path.parent
        pattern = re.compile(rf"{re.escape(path.stem)}\.(\d+){re.escape(path.suffix)}$")
        numbers = [
            int(match.group(1)) for fname in listdir(directory) if (match := pattern.match(fname))
        ]
        next_num = max(numbers) + 1 if numbers else 1
        return directory / f"{path.stem}.{next_num}{path.suffix}"

    @staticmethod
    def _generate_ips(offset: int, max_count: int) -> list[str]:
        ips: list[str] = []
        for idx, (x, y, z) in enumerate(
            [(x, y, z) for x in range(256) for y in range(256) for z in range(1, 255)]
        ):
            if idx < offset:
                continue
            ips.append(f"127.{x}.{y}.{z}")
            if len(ips) >= max_count:
                break
        return ips

    @staticmethod
    def generate_hosts(
        host_count: int,
        central_site: Site,
        target_sites: list[Site] | None = None,
        host_ip_offset: int = 0,
        folder: str = "/",
        target_site_ids: list[str] | None = None,
    ) -> list[dict[str, object]]:
        site_ids = target_site_ids or [site.id for site in (target_sites or [central_site])]
        unixtime = int(time())
        hosts = []
        for site_id in site_ids:
            is_central_site = site_id == central_site.id
            for idx, ip in enumerate(
                PerformanceTest._generate_ips(host_ip_offset, host_count), start=1
            ):
                hostname = f"{site_id}_{unixtime}_{idx}"
                entry: dict[str, object] = {
                    "host_name": hostname,
                    "folder": folder,
                    "attributes": {
                        "ipaddress": ip,
                        "tag_agent": "cmk-agent",
                        "tag_address_family": "ip-v4-only",
                    },
                }
                if (not is_central_site) and isinstance(entry["attributes"], dict):
                    entry["attributes"]["site"] = site_id
                hosts.append(entry)
        return hosts

    @staticmethod
    def generate_piggyback_hosts(
        host_count: int,
        central_site: Site,
        target_sites: list[Site] | None = None,
        folder: str = "/",
        target_site_ids: list[str] | None = None,
    ) -> list[dict[str, object]]:
        """Generate piggybacked host entries, distributed over the given target sites.

        host_count piggybacked hosts are generated for each target site.
        """
        site_ids = target_site_ids or [site.id for site in (target_sites or [central_site])]
        unixtime = int(time())
        hosts: list[dict[str, object]] = []
        for site_id in site_ids:
            for idx in range(1, host_count + 1):
                attributes: dict[str, object] = {
                    "tag_address_family": "no-ip",
                    "tag_agent": "no-agent",
                    "tag_piggyback": "piggyback",
                }
                if site_id != central_site.id:
                    attributes["site"] = site_id
                hosts.append(
                    {
                        "host_name": f"{site_id}_pb_{unixtime}_{idx}",
                        "folder": folder,
                        "attributes": attributes,
                    }
                )
        return hosts

    def await_broker_ready(self, timeout: int = 180, check_shovels: bool = True) -> None:
        """Wait until the message broker of each site is up and all shovels are running.

        With check_shovels=False only the broker ports are awaited. This is needed
        when the remote sites are mocked: the central broker's shovels towards the
        mocked sites can never establish a connection.
        """
        for site in self.sites:
            port = site.get_config("RABBITMQ_PORT")
            for _ in range(timeout):
                if site.execute(["rabbitmq-diagnostics", "check_port_listener", port]).wait() == 0:
                    break
                sleep(1)
            else:
                raise TimeoutError(
                    f'Message broker of site "{site.id}" is not listening on port {port}!'
                )
        if not check_shovels:
            return
        for site in self.sites:
            for _ in range(timeout):
                shovel_status = site.run(
                    ["rabbitmqctl", "shovel_status", "--formatter", "json"], check=False
                )
                if shovel_status.returncode == 0 and all(
                    shovel["state"] == "running" for shovel in json.loads(shovel_status.stdout)
                ):
                    break
                sleep(1)
            else:
                raise TimeoutError(f'Message broker shovels of site "{site.id}" are not running!')

    @contextmanager
    def distributed_piggyback_environment(
        self,
        target_site_ids: list[str] | None = None,
        pb_hosts_per_site: int | None = None,
        check_shovels: bool = True,
    ) -> Iterator[list[str]]:
        """Provide a distributed piggyback environment.

        Enable the piggyback hub on all (real) sites and create "pb_hosts_per_site"
        (default: "object_count") piggybacked hosts on each target site (default:
        each remote site). Wait for the message broker connections between the
        sites to be established before yielding the piggybacked host names.
        """
        with ExitStack() as stack:
            for site in self.sites:
                stack.enter_context(site.omd_config("PIGGYBACK_HUB", "on"))
            hostnames = self.create_hosts(
                self.central_site,
                self.generate_piggyback_hosts(
                    pb_hosts_per_site or self.object_count,
                    self.central_site,
                    self.remote_sites or None,
                    target_site_ids=target_site_ids,
                ),
            )
            try:
                self.await_broker_ready(check_shovels=check_shovels)
                yield hostnames
            finally:
                self.delete_hosts(self.central_site, hostnames)

    @contextmanager
    def mocked_remote_sites_environment(
        self, count: int | None = None, activate_delay: float = 0.0
    ) -> Iterator[list[str]]:
        """Register "count" (default: "mocked_sites") mock remote sites on the central site.

        The mock sites emulate the remote side of the activate changes protocol
        (config sync, activation, broker certificates) and a minimal livestatus
        endpoint, so the central site performs its full per-site activation work
        without the resource cost of real OMD sites. See mock_remote_sites.py.
        """
        with mock_remote_site_cluster(
            count or self.mocked_sites,
            self.central_site.version,
            activate_delay=activate_delay,
        ) as cluster:
            logger.info("Registering %d mock remote sites...", len(cluster.site_ids))
            for site_id in cluster.site_ids:
                self.central_site.openapi.sites.create(cluster.site_connection_config(site_id))
                self.central_site.openapi.sites.login(
                    site_id, password=self.central_site.admin_password
                )
            self.central_site.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=True
            )
            try:
                yield cluster.site_ids
            finally:
                logger.info("Removing %d mock remote sites...", len(cluster.site_ids))
                # A failed benchmark round may leave hosts assigned to the mock
                # sites behind; they block the deletion of the site connections.
                # All generated host names start with the mock site ID.
                if leftover_hosts := [
                    hostname
                    for hostname in self.central_site.openapi.hosts.get_all_names()
                    if hostname.startswith(tuple(cluster.site_ids))
                ]:
                    logger.warning(
                        "Deleting %d leftover hosts assigned to mock sites...",
                        len(leftover_hosts),
                    )
                    self.delete_hosts(self.central_site, leftover_hosts)
                for site_id in cluster.site_ids:
                    self.central_site.openapi.sites.delete(site_id)
                self.central_site.openapi.changes.activate_and_wait_for_completion(
                    force_foreign_changes=True
                )
