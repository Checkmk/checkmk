#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Hosts the Dynamic host configuration creates from piggyback data.

The piggyback payload is pre-staged and stable, so one forced DCD run creates and discovers
every host; what is timed is that run rather than the daemon's own schedule.
"""

import logging
import subprocess

from tests.performance.perftest import PerformanceTest
from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.dcd import execute_dcd_cycle

logger = logging.getLogger(__name__)

DCD_PIGGYBACK_SOURCE_HOST = "test-performance-dcd"
DCD_PIGGYBACK_CONNECTOR_ID = "dcd_performance_piggyback"
DCD_PIGGYBACK_GENERATOR_NAME = "dump_generator.py"
# The piggyback data is pre-staged and stable, so a single forced DCD run is enough to
# create and discover all hosts. A fine-grained poll interval keeps the measurement tied
# to the actual DCD work instead of a coarse sleep grid.
DCD_PIGGYBACK_CYCLE_INTERVAL = 0.5
DCD_PIGGYBACK_CYCLE_MAX_COUNT = 240


def dcd_piggybacked_hosts(perftest: PerformanceTest) -> list[str]:
    """The deterministic set of piggybacked host names emitted by the source host."""
    return [f"{DCD_PIGGYBACK_SOURCE_HOST}-pb-{idx}" for idx in range(1, perftest.object_count + 1)]


def setup_dcd_piggyback_env(perftest: PerformanceTest) -> None:
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
    site = perftest.central_site

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
    generator_source = repo_path() / "tests/scripts/dummy_agent_dump_generator.py"
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
            str(perftest.object_count),
            "--piggyback-services",
            "10",
        ]
    )
    # Scope the rule to the source host so it can't override the datasource of any other
    # host sharing this (module-scoped) site.
    perftest.dcd_piggyback_rule_id = site.openapi.rules.create(
        ruleset_name="datasource_programs",
        value=program_call,
        conditions={"host_name": {"match_on": [DCD_PIGGYBACK_SOURCE_HOST], "operator": "one_of"}},
    )

    logger.info("Creating source host %s...", DCD_PIGGYBACK_SOURCE_HOST)
    site.openapi.hosts.create(
        hostname=DCD_PIGGYBACK_SOURCE_HOST,
        folder="/",
        attributes={"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"},
    )
    site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True, strict=False)

    logger.info("Discovering source host to stage the piggyback cache...")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(DCD_PIGGYBACK_SOURCE_HOST)
    site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True, strict=False)


def teardown_dcd_piggyback_env(perftest: PerformanceTest) -> None:
    """Remove the DCD piggyback environment."""
    site = perftest.central_site
    if site.openapi.hosts.get(DCD_PIGGYBACK_SOURCE_HOST):
        site.openapi.hosts.delete(DCD_PIGGYBACK_SOURCE_HOST)
    if perftest.dcd_piggyback_rule_id and site.openapi.rules.get(perftest.dcd_piggyback_rule_id):
        site.openapi.rules.delete(perftest.dcd_piggyback_rule_id)
        perftest.dcd_piggyback_rule_id = ""
    if site.openapi.dcd.get(DCD_PIGGYBACK_CONNECTOR_ID):
        site.openapi.dcd.delete(DCD_PIGGYBACK_CONNECTOR_ID)
    site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True, strict=False)
    site.delete_file(DCD_PIGGYBACK_GENERATOR_NAME)


def setup_dcd_piggyback_round(perftest: PerformanceTest) -> None:
    """Guarantee an identical, complete starting state before each measured round.

    Every measured round must start from the same state: zero piggybacked hosts and a
    freshly, fully populated piggyback cache. The previous round's hosts and cache are
    dropped first, the source host's check is rescheduled to regenerate the cache, and we
    wait until every piggybacked host is staged. DCD is then restarted as the *last*
    action so it picks up the freshly staged cache and its cycle timers are reset against
    it; with the connector's poll interval set very high, host creation happens only in
    the forced, measured cycle.
    """
    site = perftest.central_site

    teardown_dcd_piggyback_round(perftest)

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
        return all(host in cached for host in dcd_piggybacked_hosts(perftest))

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


def teardown_dcd_piggyback_round(perftest: PerformanceTest) -> None:
    """Drop the piggybacked hosts created by the cycle, and the piggyback cache.

    Removing the cache too means the next round's setup regenerates it from scratch, so
    the reschedule-and-wait there genuinely re-stages the data instead of finding the
    previous round's directories already in place.
    """
    site = perftest.central_site
    existing = site.openapi.hosts.get_all_names(allow=dcd_piggybacked_hosts(perftest))
    if existing:
        site.openapi.hosts.bulk_delete(existing)
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=True, strict=False
        )
    site.delete_dir("tmp/check_mk/piggyback")


def scenario_performance_dcd_piggyback(perftest: PerformanceTest) -> None:
    """Scenario (timed): one DCD run that turns the pre-staged piggyback data into hosts.

    The piggyback cache holds exactly ``object_count`` hosts (guaranteed by the per-round
    setup), so the work performed here is deterministic: force DCD cycles until all
    piggybacked hosts have been created and discovered. With stable, pre-staged input and
    a fine-grained poll interval, the measured runtime reflects the real DCD discovery
    work and is reproducible on the same machine.
    """
    execute_dcd_cycle(
        perftest.central_site,
        expected_pb_hosts=perftest.object_count,
        max_count=DCD_PIGGYBACK_CYCLE_MAX_COUNT,
        interval=DCD_PIGGYBACK_CYCLE_INTERVAL,
    )
    assert (
        len(
            perftest.central_site.openapi.hosts.get_all_names(allow=dcd_piggybacked_hosts(perftest))
        )
        == perftest.object_count
    )
