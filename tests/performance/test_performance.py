#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator
from time import time

import pytest
from pytest_benchmark.fixture import BenchmarkFixture  # type: ignore[import-untyped]

from tests.testlib.agent_dumps import dummy_agent_dump_generator
from tests.testlib.agent_hosts import piggyback_host_from_dummy_generator
from tests.testlib.common.repo import qa_test_data_path
from tests.testlib.dcd import execute_dcd_cycle
from tests.testlib.site import Site
from tests.testlib.version import CMKVersion, version_from_env

from tests.performance.sysmon import track_resources

logger = logging.getLogger(__name__)

dump_path_repo = qa_test_data_path() / "plugins_integration/dumps/piggyback"


class PerformanceTest:
    def __init__(self, sites: list[Site], config: pytest.Config) -> None:
        """Initialize the performance test with a list of sites.

        If multiple sites are given, the first site will be the central site,
        while the remaining sites will act as remote sites."""
        super().__init__()
        self._sites = sites

        self.rounds = val if isinstance((val := config.getoption("rounds")), int) else 5
        self.warmup_rounds = (
            val if isinstance((val := config.getoption("warmup_rounds")), int) else 0
        )
        self.iterations = val if isinstance((val := config.getoption("iterations")), int) else 1
        self.object_count = (
            val if isinstance((val := config.getoption("object_count")), int) else 1000
        )

    @property
    def sites(self) -> list[Site]:
        """Return the list of all sites used for the test."""
        return self._sites

    @property
    def central_site(self) -> Site:
        """Return the central site."""
        return self._sites[0]

    @property
    def remote_sites(self) -> list[Site]:
        """The list of all remote sites used for the test (if any)."""
        return self._sites[1:]

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

        Create 1000 hosts on each site (central site+remote sites).
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

        Create 1000 hosts on the central site.
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

        Create a source host with 1000 piggybacked hosts.
        Wait for piggyback host discovery.
        Remove the source hosts.
        Wait for piggyback host removal.
        """
        source_host_name = "test-performance-dcd"
        pb_host_count = 10
        with piggyback_host_from_dummy_generator(
            self.central_site, source_host_name, pb_host_count=pb_host_count
        ) as (rule_id, piggybacked_hosts):
            assert (
                len(self.central_site.openapi.hosts.get_all_names([source_host_name]))
                >= pb_host_count
            )

            # Recreate rule to change number of piggybacked hosts
            self.central_site.openapi.rules.delete(rule_id)
            self.central_site.openapi.changes.activate_and_wait_for_completion()
            with dummy_agent_dump_generator(
                self.central_site,
                pb_host_count=0,
            ):
                execute_dcd_cycle(self.central_site, expected_pb_hosts=0)


@pytest.fixture(name="perftest", scope="session")
def _perftest(central_site: Site, pytestconfig: pytest.Config) -> Iterator[PerformanceTest]:
    yield PerformanceTest([central_site], config=pytestconfig)


@pytest.fixture(name="perftest_dist", scope="session")
def _perftest_dist(
    central_site: Site, remote_site: Site, remote_site_2: Site, pytestconfig: pytest.Config
) -> Iterator[PerformanceTest]:
    yield PerformanceTest([central_site, remote_site, remote_site_2], config=pytestconfig)


def test_performance_hosts(
    perftest_dist: PerformanceTest, benchmark: BenchmarkFixture, track_resources: None
) -> None:
    """Bulk host creation"""
    benchmark.pedantic(
        perftest_dist.scenario_create_and_delete_hosts,
        args=[],
        rounds=perftest_dist.rounds,
        iterations=perftest_dist.iterations,
    )


def test_performance_hosts_restart(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk host creation"""
    benchmark.pedantic(
        perftest.scenario_create_and_delete_hosts,
        args=[perftest.rounds],  # pass the rounds to switch to restart mode
        rounds=1,  # run a single round in total
        iterations=perftest.iterations,
    )


@pytest.mark.skipif(
    version_from_env() < CMKVersion("2.4.0"),
    reason="Not supported on Checkmk versions below 2.4.0!",
)
def test_performance_services(
    perftest: PerformanceTest, benchmark: BenchmarkFixture, track_resources: None
) -> None:
    """Bulk service discovery"""
    benchmark.pedantic(
        perftest.scenario_performance_services,
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )


def test_performance_piggyback(
    perftest: PerformanceTest, benchmark: BenchmarkFixture, track_resources: None
) -> None:
    benchmark.pedantic(
        perftest.scenario_performance_dcd_piggyback,
        args=[],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
