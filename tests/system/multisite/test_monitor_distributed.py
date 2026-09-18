#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Distributed behaviour of the All hosts feed and the host overview.

The feed asks every connected monitoring site for its own capped slice, then
merges the slices and re-applies both the cap and the counts centrally. Only a
real central/remote pair exercises the fan-out, the cut and the merge together:
the request-level doubles synthesise merged rows rather than receiving them, so
a wrong cut, a lost row or a count that does not match the rows on screen is
invisible below this tier.
"""

import logging
from collections.abc import Iterator, Mapping
from typing import cast, TypedDict

import pytest
import requests

from tests.testlib.common.utils import wait_until
from tests.testlib.openapi_session import APIVersion
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

# The names interleave across the two sites on purpose: sorted ascending they
# alternate central, remote, central, ..., so a feed that returned one site's
# rows and then the other's is visibly wrong rather than accidentally right.
# They differ by a trailing letter rather than a number, so the endpoint's
# natural ordering and a plain lexicographic one agree and the expected order
# needs no assumption about which of the two is in force.
_PREFIX = "distmon"
_CENTRAL_HOSTS = [f"{_PREFIX}-a", f"{_PREFIX}-c", f"{_PREFIX}-e"]
_REMOTE_HOSTS = [f"{_PREFIX}-b", f"{_PREFIX}-d", f"{_PREFIX}-f"]
_ALL_HOSTS = sorted(_CENTRAL_HOSTS + _REMOTE_HOSTS)

# Larger than the fixture's host count, so a query carrying it is never the one
# doing the cutting when a test is about something else.
_NO_CUT = len(_ALL_HOSTS) * 10


@pytest.fixture(name="hosts_per_site", scope="module")
def _hosts_per_site(central_site: Site, remote_site: Site) -> Iterator[Mapping[str, str]]:
    """Create the hosts, half on each site; yield host name -> owning site id.

    Created through the central site for both halves, which is how a distributed
    setup is actually administered — the remote never has hosts configured on it
    directly.
    """
    owner = {
        **dict.fromkeys(_CENTRAL_HOSTS, central_site.id),
        **dict.fromkeys(_REMOTE_HOSTS, remote_site.id),
    }
    try:
        for name, site_id in owner.items():
            central_site.openapi.hosts.create(
                hostname=name,
                attributes={"ipaddress": "127.0.0.1", "site": site_id},
            )
        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        # Activating the configuration is not the same as every site's core having
        # reloaded, so the hosts reach the merged feed a moment later. Every test
        # below depends on all six being there, so wait for that, not for the
        # activation alone.
        wait_until(
            lambda: (
                {
                    host["name"]
                    for host in _list_hosts(central_site, limit=_NO_CUT, q=_PREFIX)["hosts"]
                }
                == set(_ALL_HOSTS)
            ),
            timeout=120,
            interval=2,
            condition_name="all six test hosts visible in the merged feed",
        )
        yield owner
    finally:
        # The setup is inside the try, so a creation that failed halfway is torn
        # down too. bulk_delete is all-or-nothing, so it only gets what exists.
        if created := central_site.openapi.hosts.get_all_names(allow=list(owner)):
            central_site.openapi.hosts.bulk_delete(created)
        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


class _HostRow(TypedDict):
    """Only the fields these tests read; the endpoint returns more.

    The service counts are part of the endpoint's default field set, so they
    are present without asking for them.
    """

    name: str
    site_id: str
    num_services: int
    num_services_ok: int
    num_services_warn: int
    num_services_crit: int
    num_services_unknown: int
    num_services_pending: int


class _PageMeta(TypedDict):
    matched: int
    total: int


class _HostsPage(TypedDict):
    hosts: list[_HostRow]
    meta: _PageMeta


def _list_hosts(
    site: Site,
    *,
    limit: int | None,
    q: str | None = None,
    sort: list[str] | None = None,
    filters: Mapping[str, object] | None = None,
) -> _HostsPage:
    """Ask ``site`` for the merged host feed, scoped to this module's hosts.

    ``q`` scopes the query so the counts are independent of whatever else the
    session-scoped sites happen to be monitoring.
    """
    body: dict[str, object] = {"limit": limit}
    if q is not None:
        body["q"] = q
    if sort is not None:
        body["sort"] = sort
    if filters is not None:
        body["filter"] = filters
    response = site.openapi.post("monitor/hosts", api_version=APIVersion.INTERNAL, json=body)
    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    return cast(_HostsPage, response.json())


def _names(page: _HostsPage) -> list[str]:
    return [host["name"] for host in page["hosts"]]


def _only_site(site_id: str) -> Mapping[str, object]:
    """The filter condition restricting a query to a single site."""
    return {"type": "condition", "field": "site_id", "op": "one_of", "value": [site_id]}


def _host_overview(site: Site, host_name: str, site_id: str) -> requests.Response:
    return site.openapi.get(
        f"monitor/hosts/{host_name}",
        api_version=APIVersion.INTERNAL,
        params={"site_id": site_id},
    )


@pytest.mark.medium_test_chain
@pytest.mark.usefixtures("hosts_per_site")
def test_the_row_limit_cuts_the_merged_list_and_not_each_site(central_site: Site) -> None:
    """A limit below the combined count returns the globally first rows.

    The limit reaches each site as its own cap, so both answer with their own
    first two and the merge has to re-apply the cap centrally. That central
    re-cut is what this pins: without it four rows come back. And because the
    names interleave, losing a site's rows shows up too - the second row would
    be the central site's own second host instead of the remote's first.
    """
    limit = 2

    payload = _list_hosts(central_site, limit=limit, q=_PREFIX, sort=["name:asc"])

    assert _names(payload) == _ALL_HOSTS[:limit], (
        "The limit was applied per site rather than to the merged list"
    )
    # The advertised match count describes the query, not the truncated page.
    assert payload["meta"]["matched"] == len(_ALL_HOSTS)


@pytest.mark.usefixtures("hosts_per_site")
def test_the_reported_total_counts_the_hosts_of_every_site(
    central_site: Site, remote_site: Site
) -> None:
    """``total`` describes the whole setup, not one site's own share.

    Compared against what each site alone monitors rather than against a fixed
    number, and never against their sum: the sites are session-scoped, carry
    other tests' hosts and a third site may be connected by the time this runs,
    so only the *relation* to each single site's share is stable.
    """
    # Deliberately cut to two rows: the total must describe the setup, not the page.
    whole_setup = _list_hosts(central_site, limit=2, q=_PREFIX, sort=["name:asc"])
    central_only = _list_hosts(central_site, limit=_NO_CUT, filters=_only_site(central_site.id))
    remote_only = _list_hosts(central_site, limit=_NO_CUT, filters=_only_site(remote_site.id))

    assert whole_setup["meta"]["total"] > central_only["meta"]["matched"], (
        "The total counts only the central site's hosts, not the remote's"
    )
    assert whole_setup["meta"]["total"] > remote_only["meta"]["matched"], (
        "The total counts only the remote site's hosts, not the central's"
    )


def test_hosts_are_ordered_across_the_sites_and_not_grouped_by_site(
    central_site: Site, hosts_per_site: Mapping[str, str]
) -> None:
    """One ordered list, not one site's hosts followed by the other's."""
    payload = _list_hosts(central_site, limit=_NO_CUT, q=_PREFIX, sort=["name:asc"])

    rendered = _names(payload)
    assert rendered == _ALL_HOSTS, (
        "Rows are not ordered across both sites: "
        f"{[(name, hosts_per_site.get(name)) for name in rendered]}"
    )


@pytest.mark.usefixtures("hosts_per_site")
def test_a_search_matches_hosts_on_every_site_and_sums_their_counts(
    central_site: Site, remote_site: Site
) -> None:
    """The search is broadcast to every site and the match count is the sum."""
    payload = _list_hosts(central_site, limit=_NO_CUT, q=_PREFIX)

    assert set(_names(payload)) == set(_ALL_HOSTS)
    assert {host["site_id"] for host in payload["hosts"]} == {central_site.id, remote_site.id}
    assert payload["meta"]["matched"] == len(_ALL_HOSTS)


@pytest.mark.medium_test_chain
def test_each_row_names_the_site_that_monitors_the_host(
    central_site: Site, hosts_per_site: Mapping[str, str]
) -> None:
    """A row's site is the site its host actually lives on.

    The site of a row only exists once rows from more than one site are merged;
    below this tier it is synthesised by the doubles.
    """
    payload = _list_hosts(central_site, limit=_NO_CUT, q=_PREFIX)

    assert {host["name"]: host["site_id"] for host in payload["hosts"]} == dict(hosts_per_site)


@pytest.mark.usefixtures("hosts_per_site")
def test_restricting_to_one_site_drops_the_others_but_not_the_total(
    central_site: Site, remote_site: Site
) -> None:
    """A site condition narrows the rows and the match count, never the total."""
    payload = _list_hosts(
        central_site,
        limit=_NO_CUT,
        q=_PREFIX,
        filters=_only_site(remote_site.id),
    )

    assert sorted(_names(payload)) == sorted(_REMOTE_HOSTS)
    assert payload["meta"]["matched"] == len(_REMOTE_HOSTS)
    assert payload["meta"]["total"] > payload["meta"]["matched"], (
        "The site condition narrowed the total, which should describe the whole setup"
    )


@pytest.mark.medium_test_chain
@pytest.mark.usefixtures("hosts_per_site")
def test_the_overview_reaches_the_site_that_owns_the_host(
    central_site: Site, remote_site: Site
) -> None:
    """A host monitored by the remote is answered for by that remote."""
    host_name = _REMOTE_HOSTS[0]

    response = _host_overview(central_site, host_name, remote_site.id)

    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    overview = response.json()
    assert overview["name"] == host_name
    assert overview["site_id"] == remote_site.id


@pytest.mark.usefixtures("hosts_per_site")
def test_the_overview_and_the_feed_agree_on_a_remote_host_service_counts(
    central_site: Site, remote_site: Site
) -> None:
    """Both endpoints report the counts held by the site monitoring the host.

    The counts are the part of the overview that has to be read off the owning
    site rather than assembled centrally, and the two endpoints reach it by
    different routes - a site-scoped single fetch against a merged fan-out. An
    absolute figure is not assertable here, so their agreement, and the
    overview's own total adding up, is what there is to check.
    """
    host_name = _REMOTE_HOSTS[0]

    response = _host_overview(central_site, host_name, remote_site.id)
    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    overview = response.json()
    row = next(
        host
        for host in _list_hosts(central_site, limit=_NO_CUT, q=_PREFIX)["hosts"]
        if host["name"] == host_name
    )

    counts = overview["service_counts"]
    assert counts == {
        "total": row["num_services"],
        "ok": row["num_services_ok"],
        "warn": row["num_services_warn"],
        "crit": row["num_services_crit"],
        "unknown": row["num_services_unknown"],
        "pending": row["num_services_pending"],
    }, "The overview and the merged feed disagree about the remote host's services"
    assert counts["total"] == (
        counts["ok"] + counts["warn"] + counts["crit"] + counts["unknown"] + counts["pending"]
    ), "The overview's service total does not add up from its per-state counts"


@pytest.mark.usefixtures("hosts_per_site")
def test_the_overview_is_not_found_when_the_named_site_does_not_monitor_the_host(
    central_site: Site,
) -> None:
    """Naming the wrong site for an existing host name is refused, not answered.

    The host exists in the distributed setup but not on the central site, so
    asking the central site for it must not fall back to another site's copy.
    """
    response = _host_overview(central_site, _REMOTE_HOSTS[0], central_site.id)

    assert response.status_code == 404, f"{response.status_code}: {response.text}"


@pytest.mark.usefixtures("hosts_per_site")
def test_a_search_with_a_remote_down_does_not_pass_a_partial_count_off_as_complete(
    central_site: Site, remote_site: Site
) -> None:
    """An unreachable site costs rows, and the count has to admit it.

    The dangerous outcome is not the failure but a successful-looking answer
    whose match count still claims every site's hosts while the rows on screen
    are only the reachable ones.
    """
    logger.info("Stopping site %s to search with a site unreachable", remote_site.id)
    # omd_stopped() restores the site in a finally and skips Site.stop()/start(),
    # whose leftover-process assertion and pytest.exit() on a slow start would
    # take the whole session down with them.
    with remote_site.omd_stopped():
        payload = _list_hosts(central_site, limit=_NO_CUT, q=_PREFIX)

    # Asserted with the remote back up, so a failure here leaves the session usable.
    assert set(_names(payload)) == set(_CENTRAL_HOSTS), (
        "A search with the remote down did not return exactly the reachable site's hosts"
    )
    assert payload["meta"]["matched"] == len(_CENTRAL_HOSTS), (
        "The match count does not describe exactly the reachable site's hosts"
    )
