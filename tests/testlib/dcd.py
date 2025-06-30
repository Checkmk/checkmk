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
def dcd_connector(
    site: Site,
    dcd_id: str = "dcd_connector",
    interval: int = 5,
    host_attributes: dict[str, object] | None = None,
    delete_hosts: bool = True,
    discover_on_creation: bool = True,
    no_deletion_time_after_init: int = 60,
    max_cache_age: int = 60,
    validity_period: int = 60,
    cleanup: bool = True,
) -> Iterator[None]:
    """Create and use a DCD connector for site.

    Args:
        site: The Site instance where the DCD cycle should be executed.
        dcd_id: The ID of the DCD connector.
        interval: The interval between each DCD cycle (seconds).
        host_attributes: Attributes to set on the newly created host.
        delete_hosts: Delete piggybacked hosts for which piggyback data is no longer present.
        discover_on_creation: Run service discovery on new hosts created by this connection.
        no_deletion_time_after_init: Seconds to prevent host deletion after site startup.
        max_cache_age: Seconds to keep hosts when piggyback source does not send data.
        validity_period: Seconds to continue consider outdated piggyback data as valid.
        cleanup: Specifies if the connector setup is cleaned up at the end.
    """
    logger.info("Creating a DCD connection for piggyback hosts...")
    host_attributes = host_attributes or {
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
        delete_hosts=delete_hosts,
        discover_on_creation=discover_on_creation,
        validity_period=validity_period,
        max_cache_age=max_cache_age,
        no_deletion_time_after_init=no_deletion_time_after_init,
    )
    with site.openapi.wait_for_completion(300, "get", "activate_changes"):
        site.openapi.changes.activate(force_foreign_changes=True)
    try:
        yield
    finally:
        if not cleanup:
            return
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
