#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Collect functions & objects, which use `CMKOpenApiSession` to interact with the Checkmk site.

Such helper functions & objects can be used to setup and teardown the UI tests.
So as to reduce the time it takes to execute the tests.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from tests.system.gui.testlib.host_details import HostDetails
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.site import Site

logger = logging.getLogger(__name__)
LOCALHOST_IPV4 = "127.0.0.1"


@contextmanager
def core_checks_paused(site: Site) -> Iterator[None]:
    """Hold whatever state was forced into the core for the body of the block.

    Active host and service checks are what would otherwise overwrite a state
    submitted with ``send_*_check_result``, and a recovery clears an
    acknowledgement with it. Both are site-wide switches, so they are restored
    in a finally.
    """
    logger.info("Pausing active host and service checks on %s", site.id)
    site.stop_host_checks()
    site.stop_active_services()
    try:
        yield
    finally:
        logger.info("Resuming active host and service checks on %s", site.id)
        site.start_host_checks()
        site.start_active_services()


@contextmanager
def create_and_delete_hosts(
    host_details: list[HostDetails], site: Site, allow_foreign_changes: bool = False
) -> Iterator[None]:
    logger.info("Create hosts via API")
    try:
        for host_detail in host_details:
            logger.debug("Create host: '%s' via API", host_detail.name)
            site.openapi.hosts.create(
                host_detail.name,
                attributes=host_detail.rest_api_attributes(),
            )
        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=allow_foreign_changes
        )
        yield
    finally:
        if is_cleanup_enabled():
            logger.info("Delete all hosts via API")
            for host_detail in host_details:
                logger.debug("Delete host: '%s' via API", host_detail.name)
                site.openapi.hosts.delete(host_detail.name)
            site.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=allow_foreign_changes
            )
