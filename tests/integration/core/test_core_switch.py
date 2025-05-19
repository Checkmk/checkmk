#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="switch_core", scope="function")
def _switch_core(site: Site) -> Iterator[None]:
    desired_core = "nagios"
    logger.info("Switching core to %s", desired_core)

    site.stop()

    p = site.omd("config", "show", "CORE", check=True)
    initial_core = p.stdout.strip()
    assert initial_core != desired_core, "Initial core is already the desired core."

    site.omd("config", "set", "CORE", desired_core, check=True)
    p = site.omd("config", "show", "CORE", check=True)
    assert p.stdout.strip() == desired_core

    site.start()

    yield

    logger.info("Switching core back to %s", initial_core)
    site.stop()
    site.omd("config", "set", "CORE", initial_core, check=True)
    p = site.omd("config", "show", "CORE", check=True)
    assert p.stdout.strip() == initial_core

    site.start()


@pytest.mark.skip_if_not_edition("enterprise")
def test_core_switch(site: Site, switch_core: Iterator[None]) -> None:
    """Test switching the core from cmc to nagios.

    Verify changes in the site can be activated after such core switch.
    """
    try:
        site.openapi.hosts.create(
            "test_host_core_switch", attributes={"ipaddress": site.http_address, "site": site.id}
        )
        site.openapi.changes.activate_and_wait_for_completion()
    except Exception as e:
        logger.error(e)
        raise

    finally:
        site.openapi.hosts.delete("test_host_core_switch")
        site.openapi.changes.activate_and_wait_for_completion()
