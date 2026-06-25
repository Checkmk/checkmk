#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""Integration tests for the Checkmk Maps daemon and its OMD wiring.

These run against a real site and guard the first-release blockers that unit
tests can't see: that the daemon is actually wired into OMD (config hook + init
script), starts, is reachable through the Apache reverse proxy, and that the
GUI↔daemon signed-ticket handshake works end to end.

Maps ships in every edition (including cloud).
"""

from collections.abc import Iterator

import pytest
import requests

from tests.testlib.common.utils import wait_until
from tests.testlib.openapi_session import APIVersion
from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession

_TIMEOUT = 30

# A map name only ever created and torn down by this module.
_CRUD_MAP = "integration_maps_crud"
# A host pinned to the local site so it shows up in the daemon's topology.
_MONITORED_HOST = "maps-integration-host"


def _maps_url(site: Site, path: str) -> str:
    """Full URL for a site-relative Maps path (behind the Apache /check_mk/maps proxy)."""
    return site.url_for_path(f"/{site.id}/check_mk/maps{path}")


def _maps_ticket(web: CMKWebSession) -> str:
    """Mint a signed daemon ticket from the logged-in GUI session."""
    ticket = web.get("ajax_maps_ticket.py").json()["result"]["ticket"]
    assert ticket
    return str(ticket)


def _first_connection_id(site: Site, web: CMKWebSession) -> str:
    """The id of the site's (built-in) local Livestatus connection."""
    response = requests.get(
        _maps_url(site, "/api/v1/connections"),
        headers={"X-Maps-Ticket": _maps_ticket(web)},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    connections = response.json()
    assert connections, "no Maps connection registered on the site"
    return str(connections[0]["id"])


def _topology_nodes(site: Site, web: CMKWebSession, connection_id: str) -> list[dict[str, object]]:
    response = requests.get(
        _maps_url(site, f"/api/v1/connections/{connection_id}/topology"),
        headers={"X-Maps-Ticket": _maps_ticket(web)},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return list(response.json())


def _map_config(site: Site, name: str, *, alias: str) -> dict[str, object]:
    """A minimal but complete map request config (the REST model has no defaults)."""
    return {
        "name": name,
        "alias": alias,
        "connection_id": f"cmk_{site.id}",
        "icon_size": None,
        "rotation_interval": 0,
        "sort_order": 0,
        "click_action": "link",
        "view": {"type": "static"},
        "objects": [],
    }


@pytest.fixture(name="maps_on")
def _maps_on(site: Site) -> None:
    """Skip when the Maps daemon is toggled off for this site."""
    if site.get_config("MAPS") != "on":
        pytest.skip("MAPS is disabled on this site (CONFIG_MAPS != on)")


def test_maps_config_variable_registered(site: Site) -> None:
    # The MAPS omd config hook must be shipped: without it `omd config` never
    # knows the variable, CONFIG_MAPS never lands in site.conf and the daemon
    # never starts. A registered hook returns a real on/off toggle.
    assert site.get_config("MAPS") in ("on", "off")


def test_maps_daemon_running(site: Site, maps_on: None) -> None:
    # `omd status --bare maps` reports 0 for a running service.
    statuses = site.get_omd_service_names_and_statuses("maps")
    assert statuses.get("maps") == 0, f"maps daemon is not running: {statuses}"


def test_maps_health_through_proxy(site: Site, maps_on: None) -> None:
    # The Apache reverse proxy forwards /<site>/check_mk/maps/api to the daemon's
    # Unix socket; /api/health is the anonymous liveness probe.
    response = requests.get(_maps_url(site, "/api/health"), timeout=_TIMEOUT)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_maps_daemon_survives_reload(site: Site, maps_on: None) -> None:
    # `omd reload maps` sends the init script's graceful-reload signal (SIGHUP);
    # the daemon must stay up and keep serving, not die or orphan its PID. Guards
    # the init.d reload action, which unit tests can't reach.
    reload_result = site.omd("reload", "maps")
    assert reload_result.returncode == 0, reload_result.stderr
    statuses = site.get_omd_service_names_and_statuses("maps")
    assert statuses.get("maps") == 0, f"maps daemon not running after reload: {statuses}"
    health = requests.get(_maps_url(site, "/api/health"), timeout=_TIMEOUT)
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_maps_api_rejects_request_without_ticket(site: Site, maps_on: None) -> None:
    # The /check_mk/maps prefix inherits /check_mk's exemption from the site's
    # Basic-auth realm; the daemon authenticates the signed ticket itself, so an
    # API call without one must be rejected rather than served anonymously.
    response = requests.get(_maps_url(site, "/api/v1/connections"), timeout=_TIMEOUT)
    assert response.status_code == 401


def test_maps_ticket_handshake_end_to_end(site: Site, web: CMKWebSession, maps_on: None) -> None:
    ticket_page = web.get("ajax_maps_ticket.py")
    ticket = ticket_page.json()["result"]["ticket"]
    assert ticket

    response = requests.get(
        _maps_url(site, "/api/v1/connections"),
        headers={"X-Maps-Ticket": ticket},
        timeout=_TIMEOUT,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.fixture(name="monitored_host")
def _monitored_host(site: Site, maps_on: None) -> Iterator[str]:
    """Create a host on the local site, activate it, and clean it up afterwards.

    Activation writes the host into the monitoring core, so it becomes visible to
    the daemon's Livestatus queries — the input the topology/object-details read
    path needs to return something concrete.
    """
    site.openapi.hosts.create(_MONITORED_HOST, attributes={"ipaddress": "127.0.0.1"})
    try:
        site.openapi.changes.activate_and_wait_for_completion()
        yield _MONITORED_HOST
    finally:
        site.openapi.hosts.delete(_MONITORED_HOST)
        site.openapi.changes.activate_and_wait_for_completion()


def test_maps_daemon_topology_includes_monitored_host(
    site: Site, web: CMKWebSession, monitored_host: str
) -> None:
    # The daemon fans a Livestatus query out over the connection and returns the
    # site's hosts as topology nodes. The host we just activated must show up,
    # tagged with the site it is monitored by. Wait past the daemon's topology
    # cache TTL so a pre-activation (empty) cache entry can expire and rebuild.
    connection_id = _first_connection_id(site, web)
    wait_until(
        lambda: any(
            node.get("name") == monitored_host and node.get("site_id") == site.id
            for node in _topology_nodes(site, web, connection_id)
        ),
        timeout=60,
        interval=3,
        condition_name=f"host {monitored_host} appears in the Maps topology",
    )


def test_maps_daemon_object_details_for_host(
    site: Site, web: CMKWebSession, monitored_host: str
) -> None:
    # The detail drawer fetches per-object details on demand (off the state
    # stream). The daemon must answer with the host's own row.
    connection_id = _first_connection_id(site, web)
    response = requests.get(
        _maps_url(site, f"/api/v1/connections/{connection_id}/object-details"),
        params={"type": "host", "host": monitored_host},
        headers={"X-Maps-Ticket": _maps_ticket(web)},
        timeout=_TIMEOUT,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "host"
    assert body["host_name"] == monitored_host


def test_maps_daemon_metric_history_through_proxy(
    site: Site, web: CMKWebSession, monitored_host: str
) -> None:
    # The metric-history endpoint drives the Livestatus rrddata path end to end
    # (proxy → ticket auth → connection → rrddata). A freshly created host may not
    # have RRDs yet, so the point is the wiring: a well-formed 200 with the
    # series/titles envelope, not that data already exists.
    connection_id = _first_connection_id(site, web)
    response = requests.get(
        _maps_url(site, f"/api/v1/connections/{connection_id}/metric-history"),
        params={"host": monitored_host, "service": "PING", "minutes": "60"},
        headers={"X-Maps-Ticket": _maps_ticket(web)},
        timeout=_TIMEOUT,
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["series"], dict)
    assert isinstance(body["titles"], dict)


def test_maps_rest_map_crud_round_trip(site: Site) -> None:
    # The REST API is the SPA's create/read/update/delete path; exercise it over
    # real HTTP against the on-disk pagetype store (the WSGI-level test covers
    # the same endpoints in-process). Map CRUD is not part of the stable API, so
    # every call asks for the unstable version the endpoints are registered for.
    collection = "domain-types/map/collections/all"
    obj = f"objects/map/{_CRUD_MAP}"
    star = {"If-Match": "*"}

    # Best-effort cleanup of a map left behind by an earlier failed run.
    site.openapi.delete(obj, api_version=APIVersion.UNSTABLE, headers=star)

    created = site.openapi.post(
        collection,
        api_version=APIVersion.UNSTABLE,
        json={"config": _map_config(site, _CRUD_MAP, alias="Crud")},
    )
    assert created.status_code == 200, created.text
    assert created.json()["extensions"]["is_builtin"] is False
    try:
        shown = site.openapi.get(obj, api_version=APIVersion.UNSTABLE)
        assert shown.status_code == 200
        assert shown.json()["extensions"]["config"]["alias"] == "Crud"

        listed = site.openapi.get(collection, api_version=APIVersion.UNSTABLE)
        assert _CRUD_MAP in {entry["id"] for entry in listed.json()["value"]}

        # Re-creating an existing name conflicts: 409 (not a silent overwrite nor
        # the 400 used for a malformed name), so the SPA's create dialog can tell
        # "name taken" apart and surface it on the name field.
        duplicate = site.openapi.post(
            collection,
            api_version=APIVersion.UNSTABLE,
            json={"config": _map_config(site, _CRUD_MAP, alias="Dup")},
        )
        assert duplicate.status_code == 409, duplicate.text

        edited = site.openapi.put(
            obj,
            api_version=APIVersion.UNSTABLE,
            json={"config": _map_config(site, _CRUD_MAP, alias="Renamed")},
            headers=star,
        )
        assert edited.status_code == 200
        assert (
            site.openapi.get(obj, api_version=APIVersion.UNSTABLE).json()["extensions"]["config"][
                "alias"
            ]
            == "Renamed"
        )
    finally:
        deleted = site.openapi.delete(obj, api_version=APIVersion.UNSTABLE, headers=star)
        assert deleted.status_code == 204

    assert site.openapi.get(obj, api_version=APIVersion.UNSTABLE).status_code == 404


def test_maps_rest_builtin_map_delete_rejected(site: Site) -> None:
    # Built-in maps are shipped read-only: they are flagged as such in the
    # listing and the delete endpoint refuses to remove them.
    listed = site.openapi.get("domain-types/map/collections/all", api_version=APIVersion.UNSTABLE)
    all_hosts = next(entry for entry in listed.json()["value"] if entry["id"] == "all_hosts")
    assert all_hosts["extensions"]["is_builtin"] is True
    assert all_hosts["extensions"]["can_delete"] is False

    response = site.openapi.delete(
        "objects/map/all_hosts", api_version=APIVersion.UNSTABLE, headers={"If-Match": "*"}
    )
    assert response.status_code == 403
