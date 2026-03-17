#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

"""Performance test classes"""

import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import pytest
import requests
from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import BrowserContext, Page
from requests.auth import HTTPBasicAuth

from tests.testlib.site import ADMIN_USER as site_admin_user
from tests.testlib.site import PythonHelper, Site
from tests.testlib.utils import check_output

from tests.performance.sysmon import track_resources

logger = logging.getLogger(__name__)


@dataclass
class CmkPageUrl:
    id: str
    value: str
    login: bool = True
    first_request_timeout: float = 30
    request_timeout: float = 5.0
    max_average_duration: float = 1.0


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
        login_url = urljoin(str(site.url), "login.py")
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
        path: Path, listdir: Callable[[str | Path | None], list[str]] = os.listdir
    ) -> Path:
        """
        Returns the next available filename like file.1.txt, file.2.txt, etc.
        Scans the target directory and increments based on existing files.
        """
        directory = path.parent
        pattern = re.compile(rf"{re.escape(path.stem)}\.(\d+){re.escape(path.suffix)}$")
        numbers = [
            int(match.group(1)) for fname in listdir(directory) if (match := pattern.match(fname))
        ]
        next_num = max(numbers) + 1 if numbers else 1
        return directory / f"{path.stem}.{next_num}{path.suffix}"

    @staticmethod
    def generate_ips(offset: int, max_count: int) -> list[str]:
        ips: list[str] = []
        for idx, (x, y, z) in enumerate(
            [(x, y, z) for x in range(0, 256) for y in range(0, 256) for z in range(1, 255)]
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
    ) -> list[dict[str, object]]:
        target_sites = target_sites or [central_site]
        unixtime = int(time())
        hosts = []
        for site in target_sites:
            is_central_site = site.id == central_site.id
            for idx, ip in enumerate(
                PerformanceTest.generate_ips(host_ip_offset, host_count), start=1
            ):
                hostname = f"{site.id}_{unixtime}_{idx}"
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
                    entry["attributes"]["site"] = site.id
                hosts.append(entry)
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

    def scenario_performance_ui_response(
        self, context: BrowserContext, page_url: CmkPageUrl
    ) -> None:
        """
        Scenario: UI response time.

        Sequentially issues 100 Playwright requests against the sites given page_url, appending a
        millisecond timestamp (_ts) as query parameter to avoid cache hits. Each request includes
        cache-busting headers and uses a timeout.

        Args:
            context: Playwright browser context.
            page_url: Object which describes the target URL and the timeouts for each test.

        Behavior:
        - Logs a warning if a response is non-OK (non-2xx status).
        - Logs a warning if an exception occurs during the request.
        """

        first_request_duration = 0.0
        page = self.page(self.central_site, context, page_url.login)
        site_url = urljoin(str(self.central_site.url), page_url.value).format_map(
            {"folder": "", "host": "dummy"}
        )
        parsed_url = urlparse(site_url)
        query_params = parse_qs(parsed_url.query)
        counter = self.object_count
        start_time = time()
        for i in range(counter):
            query_params["_ts"] = [f"{int(time() * 1000)}"]
            new_query = urlencode(query_params, doseq=True)
            unique_url = urlunparse(parsed_url._replace(query=new_query))
            try:
                timeout_ms = 1000 * (
                    page_url.first_request_timeout if i == 0 else page_url.request_timeout
                )
                resp = page.goto(unique_url, timeout=timeout_ms)
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
        end_time = time()
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
                            [self.sites[location_id]],
                            host_ip_offset,
                            folder=environment_folder,
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

    def setup_nagios_core_plugin_import(self) -> None:
        """Setup: Nagios core plugin import

        Executes "nagios_core_plugin_import.py --list-plugins" in the site context and stores the
        output in the file $OMD_ROOT/plugins.json.

        Args:
            None

        Returns:
            None
        """
        helper_path = Path(__file__).parent / "nagios_core_plugin_import.py"
        helper = PythonHelper(self.central_site, helper_path)
        helper_stem = helper.helper_path.stem
        self.central_site.write_file(f"var/log/{helper_stem}.log", helper.check_output())

    def scenario_nagios_core_plugin_import(self, iterations: int) -> None:
        """Scenario: Nagios core plugin import

        Sequentially runs nagios_core_plugin_import.py 10 times per iteration in the site context.

        Reads the list of plugins from the file $OMD_ROOT/plugins.json created in the setup.

        Args:
            None

        Returns:
            None
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
