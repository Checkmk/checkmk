#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Performance test classes"""

import itertools
import json
import logging
import os
import re
import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from time import sleep, time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import pytest
import requests
from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import BrowserContext, Page
from requests.auth import HTTPBasicAuth

from tests.performance.mock_remote_sites import mock_remote_site_cluster
from tests.performance.sysmon import track_resources
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import check_output
from tests.testlib.dcd import execute_dcd_cycle
from tests.testlib.site import ADMIN_USER as site_admin_user
from tests.testlib.site import PythonHelper, Site

logger = logging.getLogger(__name__)

# DCD piggyback scenario
DCD_PIGGYBACK_SOURCE_HOST = "test-performance-dcd"
DCD_PIGGYBACK_CONNECTOR_ID = "dcd_performance_piggyback"
DCD_PIGGYBACK_GENERATOR_NAME = "dump_generator.py"
# The piggyback data is pre-staged and stable, so a single forced DCD run is enough to
# create and discover all hosts. A fine-grained poll interval keeps the measurement tied
# to the actual DCD work instead of a coarse sleep grid.
DCD_PIGGYBACK_CYCLE_INTERVAL = 0.5
DCD_PIGGYBACK_CYCLE_MAX_COUNT = 240


@dataclass
class CmkPageUrl:
    id: str
    value: str
    login: bool = True
    first_request_timeout: float = 30
    request_timeout: float = 5.0
    max_average_duration: float = 3.0


class PerformanceTest:
    def __init__(
        self, central_site: Site, remote_sites: list[Site] | None, pytestconfig: pytest.Config
    ) -> None:
        """Initialize the performance test with a central site and a list of remote sites."""
        super().__init__()
        self.central_site = central_site
        self.remote_sites = remote_sites or []

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
        self._dcd_piggyback_rule_id = ""
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

    def scenario_create_and_delete_hosts(
        self,
        restart_iterations: int = 0,
    ) -> None:
        """Scenario: Bulk host creation

        Create 100 hosts on each site (central site+remote sites).
        Activate the changes.
        Delete all hosts.
        Activate the changes."""
        hosts = self.generate_hosts(self.object_count, self.central_site, self.sites)
        hostnames = self.create_hosts(self.central_site, hosts)
        assert hostnames
        try:
            if restart_iterations:
                with track_resources("restart_central_site_with_hosts"):
                    for _ in range(restart_iterations):
                        self.central_site.stop()
                        self.central_site.start()
        finally:
            if not self.central_site.is_running():
                self.central_site.start()
            self.central_site.ensure_running()
            self.delete_hosts(self.central_site, hostnames)

    def scenario_performance_services(
        self,
    ) -> None:
        """Scenario: Bulk service discovery

        Create 100 hosts on the central site.
        Activate changes.
        Discover services.
        Drop the hosts.
        Activate changes.
        """
        hosts = self.generate_hosts(self.object_count, self.central_site)
        hostnames = self.create_hosts(self.central_site, hosts)
        assert hostnames
        try:
            self.discover_services(self.central_site, hostnames)
        finally:
            existing_host_names = self.central_site.openapi.hosts.get_all_names()
            missing_host_names = [_ for _ in hostnames if _ not in existing_host_names]
            logger.info(
                "The following %s hosts have been created: %s",
                len(existing_host_names),
                existing_host_names,
            )
            if len(missing_host_names) > 0:
                logger.warning(
                    "The following %s hosts are missing: %s",
                    len(missing_host_names),
                    missing_host_names,
                )
            if len(hostnames) > 0:
                self.delete_hosts(self.central_site, hostnames)

    @property
    def dcd_piggybacked_hosts(self) -> list[str]:
        """The deterministic set of piggybacked host names emitted by the source host."""
        return [f"{DCD_PIGGYBACK_SOURCE_HOST}-pb-{idx}" for idx in range(1, self.object_count + 1)]

    def setup_dcd_piggyback_env(self) -> None:
        """Build the DCD piggyback environment, outside the benchmark measurement.

        This scaffolding is created once per test (not per measured round):
          * the piggyback DCD connector,
          * the dummy datasource program rule that emits ``object_count`` piggybacked hosts,
          * the source host whose check runs that program and fills the piggyback cache.

        The connector's host discovery is non-deterministic in *when* it runs. To keep it out
        of the measured window, the connector's poll interval is set very high (below) and the
        conftest sets ``dcd_site_update_interval = 3600``; host creation is then driven solely
        by the forced ``cmk-dcd --execute-cycle`` in the measured scenario, not by the daemon.
        """
        site = self.central_site

        logger.info("Creating DCD piggyback connector...")
        site.openapi.dcd.create_piggyback_connection(
            dcd_id=DCD_PIGGYBACK_CONNECTOR_ID,
            title="DCD connector for piggyback performance test",
            host_attributes={
                "tag_snmp_ds": "no-snmp",
                "tag_agent": "no-agent",
                "tag_piggyback": "piggyback",
                "tag_address_family": "no-ip",
            },
            # Very high on purpose: autonomous cycles are effectively disabled so host
            # creation happens only in the forced cycle of the measured scenario.
            interval=3600,
            delete_hosts=True,
            discover_on_creation=True,
            no_deletion_time_after_init=600,
            max_cache_age=3600,
            validity_period=600,
        )

        logger.info("Creating dummy datasource program rule for %s...", DCD_PIGGYBACK_SOURCE_HOST)
        generator_source = Path(__file__).parent.parent / "scripts/dummy_agent_dump_generator.py"
        site.write_file(DCD_PIGGYBACK_GENERATOR_NAME, generator_source.read_text())
        program_call = " ".join(
            [
                "python3",
                f"~/{DCD_PIGGYBACK_GENERATOR_NAME}",
                "--host-name",
                DCD_PIGGYBACK_SOURCE_HOST,
                "--service-count",
                "0",
                "--payload",
                "0",
                "--piggyback-hosts",
                str(self.object_count),
                "--piggyback-services",
                "10",
            ]
        )
        # Scope the rule to the source host so it can't override the datasource of any other
        # host sharing this (module-scoped) site.
        self._dcd_piggyback_rule_id = site.openapi.rules.create(
            ruleset_name="datasource_programs",
            value=program_call,
            conditions={
                "host_name": {"match_on": [DCD_PIGGYBACK_SOURCE_HOST], "operator": "one_of"}
            },
        )

        logger.info("Creating source host %s...", DCD_PIGGYBACK_SOURCE_HOST)
        site.openapi.hosts.create(
            hostname=DCD_PIGGYBACK_SOURCE_HOST,
            folder="/",
            attributes={"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"},
        )
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=True, strict=False
        )

        logger.info("Discovering source host to stage the piggyback cache...")
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(
            DCD_PIGGYBACK_SOURCE_HOST
        )
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=True, strict=False
        )

    def teardown_dcd_piggyback_env(self) -> None:
        """Remove the DCD piggyback environment."""
        site = self.central_site
        if site.openapi.hosts.get(DCD_PIGGYBACK_SOURCE_HOST):
            site.openapi.hosts.delete(DCD_PIGGYBACK_SOURCE_HOST)
        if self._dcd_piggyback_rule_id and site.openapi.rules.get(self._dcd_piggyback_rule_id):
            site.openapi.rules.delete(self._dcd_piggyback_rule_id)
            self._dcd_piggyback_rule_id = ""
        if site.openapi.dcd.get(DCD_PIGGYBACK_CONNECTOR_ID):
            site.openapi.dcd.delete(DCD_PIGGYBACK_CONNECTOR_ID)
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=True, strict=False
        )
        site.delete_file(DCD_PIGGYBACK_GENERATOR_NAME)

    def setup_dcd_piggyback_round(self) -> None:
        """Guarantee an identical, complete starting state before each measured round.

        Every measured round must start from the same state: zero piggybacked hosts and a
        freshly, fully populated piggyback cache. The previous round's hosts and cache are
        dropped first, the source host's check is rescheduled to regenerate the cache, and we
        wait until every piggybacked host is staged. DCD is then restarted as the *last*
        action so it picks up the freshly staged cache and its cycle timers are reset against
        it; with the connector's poll interval set very high, host creation happens only in
        the forced, measured cycle.
        """
        site = self.central_site

        self.teardown_dcd_piggyback_round()

        logger.info("Rescheduling source host check to regenerate the piggyback cache...")
        site.reschedule_services(DCD_PIGGYBACK_SOURCE_HOST, max_count=3, strict=False)

        def _piggyback_cache_fully_staged() -> bool:
            # The source host's datasource program writes one cache directory per piggybacked
            # host under tmp/check_mk/piggyback/. listdir shells out to `ls`, which fails
            # (CalledProcessError) while the directory does not exist yet.
            try:
                cached = set(site.listdir("tmp/check_mk/piggyback"))
            except subprocess.CalledProcessError:
                return False
            return all(host in cached for host in self.dcd_piggybacked_hosts)

        wait_until(
            _piggyback_cache_fully_staged,
            timeout=120,
            interval=1,
            condition_name="wait for piggyback cache to be fully staged",
        )

        logger.info("Restarting DCD so it picks up the freshly staged cache...")
        site.omd("restart", "dcd", check=True)

        # `omd restart` returns before the DCD controller socket is ready to serve commands.
        # Wait until a cycle command actually succeeds, so the measured scenario's first
        # forced cycle cannot race a not-yet-ready daemon (a flaky cmk-dcd exit 1).
        wait_until(
            lambda: site.run(["cmk-dcd", "--batches"], check=False).returncode == 0,
            timeout=60,
            interval=1,
            condition_name="wait for DCD daemon to be ready after restart",
        )

    def teardown_dcd_piggyback_round(self) -> None:
        """Drop the piggybacked hosts created by the cycle, and the piggyback cache.

        Removing the cache too means the next round's setup regenerates it from scratch, so
        the reschedule-and-wait there genuinely re-stages the data instead of finding the
        previous round's directories already in place.
        """
        site = self.central_site
        existing = site.openapi.hosts.get_all_names(allow=self.dcd_piggybacked_hosts)
        if existing:
            site.openapi.hosts.bulk_delete(existing)
            site.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=True, strict=False
            )
        site.delete_dir("tmp/check_mk/piggyback")

    def scenario_performance_dcd_piggyback(self) -> None:
        """Scenario (timed): one DCD run that turns the pre-staged piggyback data into hosts.

        The piggyback cache holds exactly ``object_count`` hosts (guaranteed by the per-round
        setup), so the work performed here is deterministic: force DCD cycles until all
        piggybacked hosts have been created and discovered. With stable, pre-staged input and
        a fine-grained poll interval, the measured runtime reflects the real DCD discovery
        work and is reproducible on the same machine.
        """
        execute_dcd_cycle(
            self.central_site,
            expected_pb_hosts=self.object_count,
            max_count=DCD_PIGGYBACK_CYCLE_MAX_COUNT,
            interval=DCD_PIGGYBACK_CYCLE_INTERVAL,
        )
        assert (
            len(self.central_site.openapi.hosts.get_all_names(allow=self.dcd_piggybacked_hosts))
            == self.object_count
        )

    def scenario_performance_ui_response(
        self, context: BrowserContext, page_url: CmkPageUrl
    ) -> None:
        """
        Scenario: UI response time.

        Sequentially issues 10 Playwright requests against the sites given page_url, appending a
        millisecond timestamp (_ts) as query parameter to avoid cache hits. Each request includes
        cache-busting headers and uses a timeout. For each request, wait for the domcontentloaded
        event being triggered.

        Args:
            context: Playwright browser context.
            page_url: Object which describes the target URL and the timeouts for each test.

        Behavior:
        - Logs a warning if a response is non-OK (non-2xx status).
        - Logs a warning if an exception occurs during the request.
        """

        first_request_duration = 0.0
        counter = 10
        page = self.page(self.central_site, context, page_url.login)
        start_time = time()
        try:
            site_url = urljoin(self.central_site.url, page_url.value).format_map(
                {"folder": "", "host": "dummy"}
            )
            parsed_url = urlparse(site_url)
            query_params = parse_qs(parsed_url.query)

            for i in range(counter):
                query_params["_ts"] = [f"{int(time() * 1000)}"]
                new_query = urlencode(query_params, doseq=True)
                unique_url = urlunparse(parsed_url._replace(query=new_query))
                try:
                    timeout_ms = 1000 * (
                        page_url.first_request_timeout if i == 0 else page_url.request_timeout
                    )
                    resp = page.goto(unique_url, timeout=timeout_ms, wait_until="domcontentloaded")
                    if i == 0:
                        first_request_duration = time() - start_time
                        logger.info(
                            'UI response "%s" - first request duration: %ss',
                            page_url.id,
                            round(first_request_duration, 3),
                        )
                    if resp and not resp.ok:
                        logger.warning(
                            'UI response "%s" - request %s failed with status %s (%s)',
                            page_url.id,
                            i,
                            resp.status,
                            unique_url,
                        )
                except Exception as exc:
                    logger.warning(
                        'UI response "%s" - request %s raised %s (%s)',
                        page_url.id,
                        i,
                        exc,
                        unique_url,
                    )
        finally:
            end_time = time()
            page.close()

        duration = end_time - start_time
        average_request_duration = (duration - first_request_duration) / (counter - 1)
        logger.info(
            'UI response "%s" - average request duration: %ss',
            page_url.id,
            round(average_request_duration, 3),
        )
        assert average_request_duration < page_url.max_average_duration

    def setup_bulk_change_activation(self) -> None:
        """Setup: Bulk change activation

        Create location folders: "site-a", "site-b" and "site-c".
        In each location folder, create system folders: "windows", "linux" and "network".
        In each system folder, create environment folders: "dev", "qa" and "prod".
        In each environment folder, create 10 hosts, which inherit a host tag from each folder.
        """
        host_tag_groups = {
            "location": [
                {"id": "site-a", "title": "Site A"},
                {"id": "site-b", "title": "Site B"},
                {"id": "site-c", "title": "Site C"},
            ],
            "system": [
                {"id": "linux", "title": "Linux"},
                {"id": "windows", "title": "Windows"},
                {"id": "network", "title": "Network Device"},
            ],
            "environment": [
                {"id": "dev", "title": "Development"},
                {"id": "qa", "title": "QA"},
                {"id": "prod", "title": "Production"},
            ],
        }
        for host_tag_group_name, host_tag_group in host_tag_groups.items():
            self.central_site.openapi.host_tag_groups.create(
                name=host_tag_group_name,
                title=host_tag_group_name.capitalize(),
                tags=host_tag_group,
            )
        host_ip_offset = 0
        host_count = 10
        target_site_id_cycle = (
            itertools.cycle(self.bulk_change_target_site_ids)
            if self.bulk_change_target_site_ids
            else None
        )
        for location_id, location in enumerate(host_tag_groups["location"]):
            self.central_site.openapi.folders.create(
                folder=location["id"],
                title=location["title"],
                attributes={"tag_location": location["id"]},
            )
            for system in host_tag_groups["system"]:
                system_folder = f"/{location['id']}/{system['id']}"
                self.central_site.openapi.folders.create(
                    folder=system_folder,
                    title=system["title"],
                    attributes={"tag_system": system["id"]},
                )
                for environment in host_tag_groups["environment"]:
                    environment_folder = f"{system_folder}/{environment['id']}"
                    self.central_site.openapi.folders.create(
                        folder=environment_folder,
                        title=environment["title"],
                        attributes={"tag_environment": environment["id"]},
                    )
                    self.central_site.openapi.hosts.bulk_create(
                        self.generate_hosts(
                            host_count,
                            self.central_site,
                            None if target_site_id_cycle else [self.sites[location_id]],
                            host_ip_offset,
                            folder=environment_folder,
                            target_site_ids=(
                                [next(target_site_id_cycle)] if target_site_id_cycle else None
                            ),
                        )
                    )
                    host_ip_offset += host_count

    def teardown_bulk_change_activation(self) -> None:
        """Teardown: Bulk change activation"""
        for location_name in ("site-a", "site-b", "site-c"):
            self.central_site.openapi.folders.delete(folder=location_name, delete_mode="recursive")
        for tag_group_name in ("location", "system", "environment"):
            self.central_site.openapi.host_tag_groups.delete(name=tag_group_name)
        assert self.central_site.openapi.changes.activate_and_wait_for_completion()

    def scenario_bulk_change_activation(self) -> None:
        """Scenario: Bulk change activation

        Setup: See setup_bulk_change_activation.
        Activate all pending changes and wait for completion.
        Teardown: See teardown_bulk_change_activation
        """
        self.central_site.ensure_running()
        assert self.central_site.openapi.changes.activate_and_wait_for_completion()

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

    def setup_nagios_core_plugin_import(self) -> None:
        """Setup: Nagios core plugin import

        Executes "nagios_core_plugin_import.py" to generate "check_localhost.py",
        which loads all agent based checks.
        """
        helper_path = Path(__file__).parent / "nagios_core_plugin_import.py"
        helper = PythonHelper(self.central_site, helper_path)
        helper_stem = helper.helper_path.stem
        self.central_site.write_file(f"var/log/{helper_stem}.log", helper.check_output())

    def scenario_nagios_core_plugin_import(self, iterations: int) -> None:
        """Scenario: Nagios core plugin import

        Sequentially runs "check_localhost.py" 10 times per iteration in the site context.

        Uses a small sampling interval to get more meaningful data.
        """
        check_path = self.central_site.path(
            "var/check_mk/core/helper_config/latest/host_checks/check_localhost.py"
        )
        assert self.central_site.file_exists(check_path), "Check file not found! Aborting."

        cmd = ["python3", check_path.as_posix()]
        logger.info("$ %s", " ".join(cmd))
        with track_resources("test_nagios_core_plugin_import", sampling_interval=0.1):
            for _ in range(iterations * 10):
                check_output(cmd, sudo=True, substitute_user=self.central_site.id)
