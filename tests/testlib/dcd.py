#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@contextmanager
def dcd_connector(site: Site, interval: int = 5, auto_cleanup: bool = True) -> Iterator[None]:
    """Create and use a DCD connector for site.

    Args:
        site: The Site instance where the DCD cycle should be executed.
        interval: The interval between each DCD cycle (seconds).
        auto_cleanup: Specifies if the connector setup is cleaned up at the end.
    """
    logger.info("Creating a DCD connection for piggyback hosts...")
    dcd_id = "dcd_connector"
    host_attributes = {
        "tag_snmp_ds": "no-snmp",
        "tag_agent": "no-agent",
        "tag_piggyback": "piggyback",
        "tag_address_family": "no-ip",
    }
    site.openapi.dcd.create(
        dcd_id=dcd_id,
        title="DCD Connector for piggyback hosts",
        host_attributes=host_attributes,
        interval=interval,
        validity_period=60,
        max_cache_age=60,
        delete_hosts=True,
        no_deletion_time_after_init=60,
    )
    with site.openapi.wait_for_completion(300, "get", "activate_changes"):
        site.openapi.changes.activate(force_foreign_changes=True)
    try:
        yield
    finally:
        if auto_cleanup:
            site.openapi.dcd.delete(dcd_id)
            site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


def execute_dcd_cycle(
    site: Site,
    expected_pb_hosts: int = 0,
    max_count: int = 30,
    interval: int = 5,
) -> None:
    """Execute a DCD cycle and wait for its completion.

    Trigger a DCD cycle until:
    1) One batch that computes all expected PB hosts is completed;
    2) The following batches also contain the expected number of PB hosts.

    This is needed to ensure that the DCD has processed all piggyback hosts and those hosts persist
    in the following batches.
    This behavior needs to be enforced considering what has been observed in CMK-24031.

    Args:
        site: The Site instance where the DCD cycle should be executed.
        expected_pb_hosts: The number of piggyback hosts expected to be discovered.
        max_count: The maxmimum number of attempts to perform when waiting for the hosts.
        interval: The delay per attempt when waiting for the hosts (seconds).
    """

    def _wait_for_hosts_in_batch() -> bool:
        site.run(["cmk-dcd", "--execute-cycle"])

        logger.info(
            "Waiting for DCD to compute the expected number of PB hosts.\nExpected PB hosts: %s",
            expected_pb_hosts,
        )
        all_batches_stdout = site.check_output(["cmk-dcd", "--batches"]).strip("\n").split("\n")
        logger.info("DCD batches:\n%s", "\n".join(all_batches_stdout[:]))

        for idx, batch_stdout in enumerate(all_batches_stdout):
            # check if there is at least one completed batch containing the expected number of PB
            # hosts
            if all(string in batch_stdout for string in ["Done", f"{expected_pb_hosts} hosts"]):
                # check that all following batches also contain the expected number of PB hosts
                if all(
                    f"{expected_pb_hosts} hosts" in next_batch_stdout
                    for next_batch_stdout in all_batches_stdout[idx + 1 :]
                ):
                    return True
        return False

    try:
        wait_until(
            _wait_for_hosts_in_batch,
            (max_count * interval) + 1,
            interval,
            "dcd: wait for hosts in DCD batch",
        )
    except TimeoutError as excp:
        excp.add_note(
            f"The expected number of piggyback hosts was not computed within {max_count} cycles."
        )
