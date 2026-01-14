#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

"""To run this test with all reporting enabled, use the following command:

$ pytest tests/performance --html=performance.htm --self-contained-html --ignore-running-procs
  --benchmark-json="benchmark.json" --benchmark-save-data --benchmark-name=long --benchmark-verbose
  --log-cli-level=INFO

For more details, see pytest --help the documentation of pytest-benchmark.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from time import time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import pytest
import requests
from playwright._impl._api_structures import SetCookieParam
from playwright.sync_api import BrowserContext, Page
from pytest_benchmark.fixture import BenchmarkFixture
from requests.auth import HTTPBasicAuth

from tests.performance.sysmon import track_resources
from tests.testlib.agent_hosts import piggyback_host_from_dummy_generator
from tests.testlib.common.repo import qa_test_data_path
from tests.testlib.site import ADMIN_USER as site_admin_user
from tests.testlib.site import Site
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger(__name__)

dump_path_repo = qa_test_data_path() / "plugins_integration/dumps/piggyback"


@dataclass
class CmkPageUrl:
    id: str
    value: str
    login: bool = True


class PerformanceTest:
    def __init__(
        self, central_site: Site, remote_sites: list[Site] | None, pytestconfig: pytest.Config
    ) -> None:
        """Initialize the performance test with a central site and a list of remote sites."""
        super().__init__()
        self.central_site = central_site
        self.remote_sites = remote_sites or []

        self.rounds = val if isinstance((val := pytestconfig.getoption("rounds")), int) else 4
        self.warmup_rounds = (
            val if isinstance((val := pytestconfig.getoption("warmup_rounds")), int) else 0
        )
        self.iterations = (
            val if isinstance((val := pytestconfig.getoption("iterations")), int) else 4
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
    def _generate_ips(offset: int, max_count: int) -> list[str]:
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

    def generate_hosts(self, host_count: int = 0) -> list[dict[str, object]]:
        host_count = host_count or self.object_count
        unixtime = int(time())
        hosts = []
        for site in self.sites:
            is_central_site = site.id == self.central_site.id
            for idx, ip in enumerate(PerformanceTest._generate_ips(0, host_count), start=1):
                hostname = f"{site.id}_{unixtime}_{idx}"
                entry: dict[str, object] = {
                    "host_name": hostname,
                    "folder": "/",
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
        hosts = self.generate_hosts(self.object_count)
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
        hosts = self.generate_hosts(self.object_count)
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

    def scenario_performance_dcd_piggyback(
        self,
    ) -> None:
        """Scenario: DCD piggyback host discovery

        Create a source host with 100 piggybacked hosts.
        Wait for piggyback host discovery.
        """
        source_host_name = "test-performance-dcd"
        pb_host_count = self.object_count
        dcd_max_count = 120
        dcd_interval = 5
        with piggyback_host_from_dummy_generator(
            self.central_site,
            source_host_name,
            pb_host_count=pb_host_count,
            dcd_max_count=dcd_max_count,
            dcd_interval=dcd_interval,
        ) as piggyback_info:
            assert len(piggyback_info.piggybacked_hosts) == pb_host_count
            assert (
                len(
                    self.central_site.openapi.hosts.get_all_names(
                        allow=piggyback_info.piggybacked_hosts
                    )
                )
                == pb_host_count
            )

    def scenario_performance_ui_response(
        self, context: BrowserContext, page_url: CmkPageUrl
    ) -> None:
        """
        Scenario: UI response time.

        Sequentially issues 100 Playwright requests against the sites given page_url, appending a
        millisecond timestamp (_ts) as query parameter to avoid cache hits. Each request includes
        cache-busting headers and uses a timeout.

        Behavior:
        - Logs a warning if a response is non-OK (non-2xx status).
        - Logs a warning if an exception occurs during the request.
        - Does not collect timing metrics or enforce performance thresholds.

        Returns:
            None

        Side Effects:
            Generates network load and may take noticeable time if the target is slow.
            Emits warning log entries for failed or errored requests.

        Potential Improvements:
            - Capture and aggregate latency metrics (e.g., min/avg/p95).
            - Add success/failure summary and assertions for automated regression detection.
            - Introduce configurable request count and concurrency for broader coverage.
        """
        max_first_request_timeout = 30  # 30 seconds until first request times out
        max_request_timeout = 0.5  # 0.5 seconds until consecutive requests time out
        max_average_request_duration = 0.3  # 0.3 seconds for the maximum average request time

        first_request_duration = 0.0
        page = self.page(self.central_site, context, page_url.login)
        site_url = urljoin(self.central_site.url, page_url.value).format_map(
            {"folder": "", "host": "dummy"}
        )
        counter = self.object_count
        start_time = time()

        for i in range(counter):
            parsed_url = urlparse(site_url)
            query_params = parse_qs(parsed_url.query)
            query_params["_ts"] = [f"{int(time() * 1000)}"]
            new_query = urlencode(query_params, doseq=True)
            unique_url = urlunparse(parsed_url._replace(query=new_query))
            try:
                timeout_ms = 1000 * (max_first_request_timeout if i == 0 else max_request_timeout)
                resp = page.goto(unique_url, timeout=timeout_ms)
                if i == 0:
                    first_request_duration = time() - start_time
                    logger.info(
                        "UI response first request duration %s (%s)",
                        first_request_duration,
                        unique_url,
                    )
                if resp and not resp.ok:
                    logger.warning(
                        "UI response request %s failed with status %s (%s)",
                        i,
                        resp.status,
                        unique_url,
                    )
            except Exception as exc:
                logger.warning("UI response request %s raised %s (%s)", i, exc, unique_url)
        end_time = time()
        duration = end_time - start_time
        average_request_duration = (duration - first_request_duration) / (counter - 1)
        assert average_request_duration < max_average_request_duration


@pytest.fixture(name="perftest", scope="session")
def _perftest(single_site: Site, pytestconfig: pytest.Config) -> Iterator[PerformanceTest]:
    """Single-site performance test"""
    yield PerformanceTest(single_site, remote_sites=None, pytestconfig=pytestconfig)


@pytest.fixture(name="perftest_dist", scope="session")
def _perftest_dist(
    central_site: Site, remote_site: Site, remote_site_2: Site, pytestconfig: pytest.Config
) -> Iterator[PerformanceTest]:
    """Distributed performance test with 2 remote sites"""
    yield PerformanceTest(
        central_site, remote_sites=[remote_site, remote_site_2], pytestconfig=pytestconfig
    )


def test_performance_hosts(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    """Bulk host creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest_dist.scenario_create_and_delete_hosts,
        args=[],
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )


def test_performance_hosts_restart(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk host creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_create_and_delete_hosts,
        args=[perftest.iterations],  # pass the iterations to switch to restart mode
        rounds=perftest.rounds,
        iterations=1,  # run a single time (iterations passed to scenario)
    )


@pytest.mark.skipif(
    version_from_env() < CMKVersion("2.4.0"),
    reason="Not supported on Checkmk versions below 2.4.0!",
)
def test_performance_services(
    perftest: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    """Bulk service discovery"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_performance_services,
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )


@pytest.mark.skip("CMK-27171: Unstable scenario; fix in progress")
def test_performance_piggyback(
    perftest: PerformanceTest, benchmark: BenchmarkFixture, track_system_resources: None
) -> None:
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_performance_dcd_piggyback,
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )


@pytest.mark.parametrize(
    "page_url",
    [
        CmkPageUrl("login", "login.py", login=False),
        CmkPageUrl("edit_host", "wato.py?folder={folder}&host={host}&mode=edit_host"),
        CmkPageUrl("service_discovery", "wato.py?folder={folder}&host={host}&mode=inventory"),
        CmkPageUrl("host_parameters", "wato.py?folder={folder}&host={host}&mode=object_parameters"),
    ],
    ids=lambda url: url.id,
)
def test_performance_ui_response(
    perftest: PerformanceTest,
    benchmark: BenchmarkFixture,
    track_system_resources: None,
    page_url: CmkPageUrl,
    context: BrowserContext,
) -> None:
    print(f"Checking {page_url.value}...")
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        perftest.scenario_performance_ui_response,
        args=[context, page_url],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
