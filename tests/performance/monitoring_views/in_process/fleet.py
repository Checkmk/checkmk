#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""How a fleet of fake sites is configured into a central site.

Kept out of ``conftest.py`` on purpose: a test module importing from a conftest gets it
imported a second time under a different module identity, and this stack has import-time side
effects (the path faking) that must happen exactly once.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

from cmk.ccc.site import SiteId
from cmk.livestatus_client import SiteConfiguration, SiteConfigurations

from ..livestatus_fake import EstateShape, QueryLog

#: The site the GUI under test runs as. ``NO_SITE`` is what the GUI test environment names it.
CENTRAL_SITE_ID = "NO_SITE"


def remote_site_id(index: int) -> str:
    return f"remote{index:02d}"


def fleet_site_ids(remote_count: int) -> list[str]:
    return [CENTRAL_SITE_ID, *(remote_site_id(index) for index in range(remote_count))]


def site_configurations(site_ids: list[SiteId]) -> SiteConfigurations:
    """Configure the fleet the way a distributed setup configures status-only connections.

    ``replication=None`` is the point: these sites are read, never written to. That is all a
    monitoring page needs, and it means no configuration sync, no message broker and no remote
    GUI has to exist for the measurement - which is also why the fleet can be faked at all.
    """
    return SiteConfigurations(
        {
            site_id: SiteConfiguration(
                id=site_id,
                alias=f"Site {site_id}",
                # The socket is never opened: the fleet replaces the client's socket. It still
                # has to parse, because the connection is built before it is used.
                socket=("local", None),
                proxy=None,
                replication=None,
                disabled=False,
                disable_wato=True,
                insecure=False,
                multisiteurl="",
                persist=False,
                replicate_ec=False,
                replicate_mkps=False,
                message_broker_port=5672,
                status_host=None,
                timeout=10,
                url_prefix="",
                user_login=True,
                is_trusted=False,
            )
            for site_id in site_ids
        }
    )


#: Stands up a fleet of a size the caller chooses, rather than the one the command line asked
#: for. The block it opens yields the log of everything the fleet was asked while it was up.
type FleetBuilder = Callable[[int, EstateShape], AbstractContextManager[QueryLog]]
