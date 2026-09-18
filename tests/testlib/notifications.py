#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Setup & teardown helpers for the notification tests."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import NamedTuple

from cmk.livestatus_client import MKLivestatusException
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

# Checkmk creates this service for every agent-based host, so it exists without discovering
# any agent data.
_SEEDED_SERVICE = "Check_MK"


class NotificationTarget(NamedTuple):
    """A host and one of its services, both seeded to a known state.

    Produced by `create_notification_host`: the service is part of what that helper
    guarantees, so tests take its name from here rather than hardcoding it.
    """

    host_name: str
    service_name: str


def _is_service_monitored(site: Site, host_name: str, service_name: str) -> bool:
    try:
        return bool(
            site.live.query(
                "GET services\nColumns: description\n"
                f"Filter: host_name = {host_name}\n"
                f"Filter: service_description = {service_name}\n"
            )
        )
    except MKLivestatusException:
        # The socket can vanish for a moment while the core re-reads its config.
        return False


@contextmanager
def create_host(site: Site, host_name: str) -> Generator[str]:
    """Create a host that pings but has no agent behind it, and delete it afterwards."""
    try:
        logger.info("Create host '%s'", host_name)
        site.openapi.hosts.create(
            host_name,
            attributes={"ipaddress": "127.0.0.1", "tag_agent": "cmk-agent"},
        )
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        yield host_name
    finally:
        if is_cleanup_enabled() and site.openapi.hosts.get(host_name) is not None:
            logger.info("Clean up: delete host '%s'", host_name)
            site.openapi.hosts.delete(host_name)
            site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@contextmanager
def create_notification_host(site: Site, host_name: str) -> Generator[NotificationTarget]:
    """Create a host whose service state the test sets explicitly.

    Yields the host and its seeded service. The test sets that service's state with
    `site.send_service_check_result(...)`. Nothing else changes it, so every notification
    the test sees is one it triggered itself.

    Service checks are switched off in the core, so no real check can overwrite a result
    the test submitted; results sent from outside are still accepted. The service is
    seeded with OK, so the first state the test submits is reported as 'OK -> <state>'.
    """
    # Stop the checks before the host exists: the host has no agent behind it, so the first
    # check the core gets round to reports a problem and notifies about it.
    site.stop_active_services()
    try:
        with create_host(site, host_name):
            # The core learns about the host only once it has re-read its config, which
            # happens asynchronously after the activation.
            wait_until(
                lambda: _is_service_monitored(site, host_name, _SEEDED_SERVICE),
                timeout=60,
                interval=1,
                condition_name=f"service '{_SEEDED_SERVICE}' of host '{host_name}' is monitored",
            )
            site.send_service_check_result(
                host_name, _SEEDED_SERVICE, 0, "FAKE OK", expected_state=0
            )
            yield NotificationTarget(host_name=host_name, service_name=_SEEDED_SERVICE)
    finally:
        # Restored regardless of `is_cleanup_enabled`: the setting is site-wide, so leaving
        # it off would stop the checks of every later test in the session.
        site.start_active_services()
