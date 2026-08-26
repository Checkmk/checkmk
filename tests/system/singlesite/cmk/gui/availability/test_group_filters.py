#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Group filters of a grouped availability view (CMK-35309).

A Livestatus filter selects rows, but a matching row also carries the groups the user did
not select. The availability view has to drop those, otherwise they show up as additional
group tables. These tests drive the real page so that the filters, the Livestatus query and
the grouping are exercised together.
"""

import logging
from collections.abc import Iterator, Mapping
from contextlib import suppress

import pytest
from bs4 import BeautifulSoup

from tests.testlib.openapi_session import UnexpectedResponse
from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession

logger = logging.getLogger(__name__)

# Group memberships are chosen so that every filtered row carries a group that was not
# selected. Without them a wrong implementation cannot be told apart from a correct one.
_HOSTS: Mapping[str, tuple[str, ...]] = {
    "av-host-ac": ("a", "c"),
    "av-host-ab": ("a", "b"),
    "av-host-c": ("c",),
    "av-host-d": ("d",),
}
_HOST_FILTER = "^av-host-"
_KEYS = ("a", "b", "c", "d")
# Aliases are the titles of the group tables. They have to be unique across all group
# types, so host and service groups cannot share them.
_HOST_GROUP_ALIASES = {key: f"Availability host group {key.upper()}" for key in _KEYS}
_SERVICE_GROUP_ALIASES = {key: f"Availability service group {key.upper()}" for key in _KEYS}
_ALL_ALIASES = set(_HOST_GROUP_ALIASES.values()) | set(_SERVICE_GROUP_ALIASES.values())


def _host_group(key: str) -> str:
    return f"av-hg-{key}"


def _service_group(key: str) -> str:
    return f"av-sg-{key}"


def _hosts_of_group(key: str) -> list[str]:
    return [host for host, keys in _HOSTS.items() if key in keys]


@pytest.fixture(name="grouped_hosts", scope="module")
def fixture_grouped_hosts(site: Site) -> Iterator[None]:
    """Ping-only hosts whose PING service belongs to overlapping host and service groups"""
    rule_ids: list[str] = []
    host_groups: list[str] = []
    service_groups: list[str] = []
    try:
        for host in _HOSTS:
            site.openapi.hosts.create(
                hostname=host,
                attributes={
                    "tag_address_family": "ip-v4-only",
                    "ipaddress": "127.0.0.1",
                    "tag_agent": "no-agent",
                },
            )
        rule_ids.append(
            site.openapi.rules.create(
                ruleset_name="host_check_commands",
                value="ping",
                conditions={"host_name": {"match_on": list(_HOSTS), "operator": "one_of"}},
            )
        )
        for key in _KEYS:
            hosts = _hosts_of_group(key)
            site.openapi.host_groups.create(name=_host_group(key), alias=_HOST_GROUP_ALIASES[key])
            host_groups.append(_host_group(key))
            site.openapi.service_groups.create(
                name=_service_group(key), alias=_SERVICE_GROUP_ALIASES[key]
            )
            service_groups.append(_service_group(key))
            rule_ids.append(
                site.openapi.rules.create(
                    ruleset_name="host_groups",
                    value=_host_group(key),
                    conditions={"host_name": {"match_on": hosts, "operator": "one_of"}},
                )
            )
            rule_ids.append(
                site.openapi.rules.create(
                    ruleset_name="service_groups",
                    value=_service_group(key),
                    conditions={
                        "host_name": {"match_on": hosts, "operator": "one_of"},
                        "service_description": {"match_on": ["PING"], "operator": "one_of"},
                    },
                )
            )

        site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
        for host in _HOSTS:
            site.wait_until_service_has_been_checked(host, "PING")

        yield
    finally:
        # Clean up what was created: a failure halfway through must not hide itself behind
        # a follow-up error of the teardown.
        for rule_id in rule_ids:
            with suppress(UnexpectedResponse):
                site.openapi.rules.delete(rule_id)
        with suppress(UnexpectedResponse):
            site.openapi.hosts.bulk_delete(list(_HOSTS))
        for host_group in host_groups:
            with suppress(UnexpectedResponse):
                site.openapi.host_groups.delete(host_group)
        for service_group in service_groups:
            with suppress(UnexpectedResponse):
                site.openapi.service_groups.delete(service_group)
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


def _group_titles(
    site: Site,
    web: CMKWebSession,
    grouping: str | None,
    filters: Mapping[str, str],
) -> set[str]:
    """Render the availability of all PING services and return the group table titles

    The grouping is set through the user's stored availability options instead of the
    option form, so that the request only carries the filters under test.
    """
    site.write_file(
        "var/check_mk/web/cmkadmin/avoptions.mk",
        repr({"grouping": grouping, "rangespec": ("age", 3600)}),
    )
    response = web.get(
        "view.py",
        params={
            "view_name": "allservices",
            "mode": "availability",
            "host_regex": _HOST_FILTER,
            **filters,
        },
    )
    soup = BeautifulSoup(response.text, "html.parser")
    return {title.get_text(strip=True) for title in soup.select("h3.table")}


def _host_aliases(*keys: str) -> set[str]:
    return {_HOST_GROUP_ALIASES[key] for key in keys}


def _service_aliases(*keys: str) -> set[str]:
    return {_SERVICE_GROUP_ALIASES[key] for key in keys}


@pytest.mark.parametrize(
    "filters, expected",
    [
        pytest.param({}, _service_aliases(*_KEYS), id="no group filter"),
        pytest.param(
            {"servicegroups": _service_group("a")},
            _service_aliases("a"),
            # The rows of group A are also in B and C, which must not become own tables
            id="several service groups",
        ),
        pytest.param(
            {"servicegroups": _service_group("a"), "neg_servicegroups": "on"},
            _service_aliases("c", "d"),
            # Livestatus already drops every row of group A, so B goes away with it
            id="negated several service groups",
        ),
        pytest.param(
            {"optservice_group": _service_group("a")},
            _service_aliases("a"),
            id="service is in group",
        ),
        pytest.param(
            {
                "servicegroups": f"{_service_group('a')}|{_service_group('b')}",
                "optservice_group": _service_group("b"),
                "neg_optservice_group": "on",
            },
            _service_aliases("a"),
            # This is the case of CMK-35309: the selection above is dropped entirely
            # because of the negated filter, so group C shows up as well
            id="several service groups with negated single group",
            marks=pytest.mark.xfail(
                strict=True,
                reason="CMK-35309: a negated group filter drops the positive selection",
            ),
        ),
        pytest.param(
            {
                "servicegroups": _service_group("a"),
                "neg_servicegroups": "on",
                "optservice_group": _service_group("c"),
                "neg_optservice_group": "on",
            },
            _service_aliases("d"),
            id="both service group filters negated",
        ),
    ],
)
@pytest.mark.usefixtures("grouped_hosts")
def test_availability_grouped_by_service_groups(
    site: Site,
    web: CMKWebSession,
    filters: Mapping[str, str],
    expected: set[str],
) -> None:
    assert _group_titles(site, web, "service_groups", filters) & _ALL_ALIASES == expected


@pytest.mark.parametrize(
    "filters, expected",
    [
        pytest.param(
            {},
            _host_aliases(*_KEYS),
            id="no group filter",
            marks=pytest.mark.xfail(
                strict=True,
                reason="CMK-35309: an empty host group filter of the view context "
                "removes every host group",
            ),
        ),
        pytest.param(
            {"hostgroups": _host_group("a")}, _host_aliases("a"), id="several host groups"
        ),
        pytest.param(
            {"hostgroups": _host_group("a"), "neg_hostgroups": "on"},
            _host_aliases("c", "d"),
            id="negated several host groups",
        ),
        pytest.param(
            {
                "hostgroups": f"{_host_group('a')}|{_host_group('b')}",
                "opthost_group": _host_group("b"),
                "neg_opthost_group": "on",
            },
            _host_aliases("a"),
            id="several host groups with negated single group",
            marks=pytest.mark.xfail(
                strict=True,
                reason="CMK-35309: a negated group filter drops the positive selection",
            ),
        ),
        pytest.param(
            {"servicegroups": _service_group("a")},
            # A service group filter selects the rows, but must not remove a host group:
            # the two hosts of service group A are in the host groups A, B and C.
            _host_aliases("a", "b", "c"),
            id="service group filter does not restrict host groups",
            marks=pytest.mark.xfail(
                strict=True,
                reason="CMK-35309: an empty host group filter of the view context "
                "removes every host group",
            ),
        ),
    ],
)
@pytest.mark.usefixtures("grouped_hosts")
def test_availability_grouped_by_host_groups(
    site: Site,
    web: CMKWebSession,
    filters: Mapping[str, str],
    expected: set[str],
) -> None:
    assert _group_titles(site, web, "host_groups", filters) & _ALL_ALIASES == expected


@pytest.mark.usefixtures("grouped_hosts")
def test_availability_grouped_by_host_ignores_group_filters(site: Site, web: CMKWebSession) -> None:
    titles = _group_titles(
        site,
        web,
        "host",
        {
            "servicegroups": f"{_service_group('a')}|{_service_group('b')}",
            "optservice_group": _service_group("b"),
            "neg_optservice_group": "on",
        },
    )
    assert titles & _ALL_ALIASES == set()
    assert "av-host-ac" in titles


@pytest.mark.usefixtures("grouped_hosts")
def test_availability_without_grouping_has_no_group_tables(site: Site, web: CMKWebSession) -> None:
    titles = _group_titles(site, web, None, {"servicegroups": _service_group("a")})
    assert titles & _ALL_ALIASES == set()
