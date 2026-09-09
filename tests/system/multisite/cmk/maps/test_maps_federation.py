#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""Distributed (multisite) behaviour of the Checkmk Maps daemon.

Regression guard for "a flow map shows only the local site's hosts" on a
distributed setup: the daemon must fan its Livestatus queries out across the
connected remote sites, not just the central site's own socket.

Two failure modes are covered end to end, both invisible to the unit tests:

* the GUI must (re)generate the prepared ``maps.d/sitespecs.mk`` fan-out specs on
  *every activation*, not only when the distributed-monitoring config is saved
  through WATO (``cmk.maps.gui._sites``) — otherwise a distributed setup that
  predates Maps, or one configured outside the WATO save flow, never gets them;
  and
* the already-running daemon must adopt those specs *without a restart* when they
  first appear (``LivestatusConnection._adopt_sites_if_appeared``).

The ``remote_site`` fixture connects the remote AFTER the central site's daemon
is already running, so the specs appear at the daemon's feet mid-flight — exactly
the "add a remote to a live central" / "install Maps onto an existing distributed
central" scenario. A daemon that latched its single-socket mode at startup (or a
GUI that only wrote the specs on ``sites-saved``) leaves the remote host out of
the topology, which is what this test would catch.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests

from tests.testlib.common.utils import wait_until
from tests.testlib.system.site import Site
from tests.testlib.system.web_session import CMKWebSession

_MAPS_SETTINGS_PATH = Path("etc/check_mk/maps.d/wato/global.mk")

logger = logging.getLogger(__name__)

_FOLDER = "maps_federation"
_HOST_NAME = "maps-federation-remote-host"
_CENTRAL_HOST_NAME = "maps-federation-central-host"
_HTTP_TIMEOUT = 30


@pytest.fixture(name="maps_on")
def _maps_on(central_site: Site) -> None:
    """Skip when the Maps daemon is toggled off for the central site."""
    if central_site.get_config("MAPS") != "on":
        pytest.skip("MAPS is disabled on the central site (CONFIG_MAPS != on)")


@pytest.fixture(name="central_monitored_host")
def _central_monitored_host(central_site: Site) -> Iterator[str]:
    """A host monitored by the central site itself.

    A fresh central site has no hosts of its own, so without this the federated
    topology would legitimately carry only the remote's host — and the
    "federation is additive, not a swap" assertion could never distinguish a
    correct additive fan-out from one that dropped the central site. This gives
    the central a host of its own so both sites must appear.
    """
    central_site.openapi.hosts.create(
        _CENTRAL_HOST_NAME, attributes={"ipaddress": "127.0.0.1", "site": central_site.id}
    )
    try:
        central_site.openapi.changes.activate_and_wait_for_completion()
        yield _CENTRAL_HOST_NAME
    finally:
        central_site.openapi.hosts.delete(_CENTRAL_HOST_NAME)
        central_site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(name="remote_monitored_host")
def _remote_monitored_host(central_site: Site, remote_site: Site) -> Iterator[str]:
    """A host pinned to — and thus monitored by — the remote site.

    Creating it through the central site's Setup and activating writes the
    prepared site specs via the ``pre-activate-changes`` hook, so the assertion
    exercises the activation-time regeneration path.
    """
    central_site.openapi.folders.create(f"/{_FOLDER}", attributes={"site": remote_site.id})
    central_site.openapi.hosts.create(
        _HOST_NAME, folder=f"/{_FOLDER}", attributes={"ipaddress": "127.0.0.1"}
    )
    try:
        central_site.openapi.changes.activate_and_wait_for_completion()
        yield _HOST_NAME
    finally:
        central_site.openapi.hosts.delete(_HOST_NAME)
        central_site.openapi.folders.delete(f"/{_FOLDER}")
        central_site.openapi.changes.activate_and_wait_for_completion()


def _maps_url(site: Site, path: str) -> str:
    """Full URL for a site-relative Maps path (behind the Apache ``/check_mk/maps`` proxy)."""
    return site.url_for_path(f"/{site.id}/check_mk/maps{path}")


def _maps_ticket(web: CMKWebSession) -> str:
    """Mint a signed daemon ticket from the logged-in GUI session."""
    ticket = web.get("ajax_maps_ticket.py").json()["result"]["ticket"]
    assert ticket
    return str(ticket)


def _first_connection_id(central_site: Site, web: CMKWebSession) -> str:
    response = requests.get(
        _maps_url(central_site, "/api/v1/connections"),
        headers={"X-Maps-Ticket": _maps_ticket(web)},
        timeout=_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    connections = response.json()
    assert connections, "no Maps connection registered on the central site"
    return str(connections[0]["id"])


def _topology_nodes(
    central_site: Site, web: CMKWebSession, connection_id: str
) -> list[dict[str, object]]:
    response = requests.get(
        _maps_url(central_site, f"/api/v1/connections/{connection_id}/topology"),
        headers={"X-Maps-Ticket": _maps_ticket(web)},
        timeout=_HTTP_TIMEOUT,
    )
    response.raise_for_status()
    return list(response.json())


def _remote_host_visible(
    central_site: Site, remote_site: Site, web: CMKWebSession, connection_id: str
) -> bool:
    return any(
        node.get("name") == _HOST_NAME and node.get("site_id") == remote_site.id
        for node in _topology_nodes(central_site, web, connection_id)
    )


def test_maps_daemon_federates_remote_site_hosts(
    central_site: Site,
    remote_site: Site,
    maps_on: None,
    central_monitored_host: str,
    remote_monitored_host: str,
) -> None:
    web = CMKWebSession(central_site)
    web.login()
    connection_id = _first_connection_id(central_site, web)

    # The daemon started single-socket (the remote was connected afterwards), so
    # reaching the remote host proves it adopted the fan-out specs live. Timeout
    # comfortably exceeds the daemon's topology cache TTL so a pre-federation
    # cache entry can expire and be rebuilt.
    wait_until(
        lambda: _remote_host_visible(central_site, remote_site, web, connection_id),
        timeout=120,
        interval=3,
        condition_name=(
            f"remote host {_HOST_NAME} ({remote_site.id}) appears in the Maps topology"
        ),
    )

    # Federation is additive, not a swap: the central site's own hosts must stay
    # visible alongside the remote's.
    site_ids = {node.get("site_id") for node in _topology_nodes(central_site, web, connection_id)}
    assert remote_site.id in site_ids
    assert central_site.id in site_ids


def test_maps_config_domain_replicated_to_remote(
    central_site: Site,
    remote_site: Site,
    maps_on: None,
    remote_monitored_host: str,
) -> None:
    """The Maps config domain must reach remote sites on Activate Changes.

    The daemon reads its runtime config (the ``maps_connections`` the SPA queries
    against) from ``etc/check_mk/maps.d/wato`` — a directory shipped by the config
    domain's ``ReplicationPath``. The ``remote_monitored_host`` fixture already ran
    a distributed Activate Changes, so the directory (and the central's settings)
    must have landed on the remote; without the registered ReplicationPath the
    remote daemon would read nothing and its maps would be empty.

    ``needs_sync = True`` — the property that lets a Maps-*only* change trigger the
    sync — is pinned at unit level (``test_config_domain.py``); this pins the
    delivery + path end to end on a real distributed setup.
    """
    assert remote_site.is_dir("etc/check_mk/maps.d/wato"), (
        "Maps config domain directory was not replicated to the remote site"
    )
    # The sample-config generator seeds maps_connections on a fresh site, so the
    # central has a global.mk; the replicated copy on the remote must carry the
    # same daemon-consumed connection list.
    if central_site.file_exists(str(_MAPS_SETTINGS_PATH)):
        assert remote_site.file_exists(str(_MAPS_SETTINGS_PATH)), (
            "Maps global.mk present on the central but missing on the remote"
        )
        assert "maps_connections" in remote_site.read_global_settings(_MAPS_SETTINGS_PATH)
