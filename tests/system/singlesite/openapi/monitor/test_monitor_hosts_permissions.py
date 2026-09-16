#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""CMK-38731 regression: a filter value carrying a "\r" must still produce a single,
correctly-``AuthUser``-scoped Livestatus count query for a restricted user.

Only a real running site can reproduce the actual bypass: the mock Livestatus used by the
``tests/openapi`` tier treats every socket write as exactly one opaque query, so it cannot
reproduce a caller-injected blank line splitting a query into two requests on the wire - which
is the mechanism the bypass relies on. The fix closes this at its root, in
cmk-livestatus-client: headers are only ever split on a real "\n", the one character Livestatus
itself treats as a line boundary (see ``LqSafe``/``lqencode``). A "\r" is not filtered or
rejected - it is simply no longer treated as a line boundary and stays inert, literal data, so
it can no longer split a query in two.

Every other angle of this ticket - rejecting a real "\n" in a filter value, on both the hosts
and host-services endpoints - is exercised at the unit level instead (see
``tests/unit/cmk/gui/monitor`` and ``packages/cmk-livestatus-client/tests``), where a mock
connection can assert on the exact query text.
"""

from collections.abc import Iterator

import pytest
import requests

from cmk.ccc.hostaddress import HostName
from tests.testlib.openapi_session import APIVersion
from tests.testlib.site import Site

_CONTACT_GROUP = "cg-38731"
_VISIBLE_HOST = HostName("h-seen-38731")
_HIDDEN_HOST = HostName("h-hidden-38731")
_RESTRICTED_USER = "low-38731"
_RESTRICTED_PASSWORD = "askjdh38731CMK!"

# The ticket's own PoC: literal CRs that, pre-fix, survived a guard excluding only "\n" and then
# became an extra blank line once re-split by str.splitlines() and rejoined - which Livestatus
# reads as the end of one request and the start of a second, unauthenticated one. Post-fix, "\r"
# is ordinary data to every step that assembles the query, so this value is legal input; the
# query it produces must still return the restricted user's own, correctly scoped count.
_CR_INJECTION_PAYLOAD = (
    "h-\rOutputFormat: python3\rResponseHeader: fixed16\rKeepAlive: on\r\rColumns: name"
)


def _no_contactgroups() -> dict[str, object]:
    """Forces a host to have no monitoring contact group, overriding any folder-level default."""
    return {
        "groups": [],
        "recurse_perms": False,
        "use": True,
        "use_for_services": True,
        "recurse_use": False,
    }


def _contactgroups(*groups: str) -> dict[str, object]:
    return {
        "groups": list(groups),
        "recurse_perms": False,
        "use": True,
        "use_for_services": True,
        "recurse_use": False,
    }


@pytest.fixture(name="contact_group_and_hosts")
def fixture_contact_group_and_hosts(site: Site) -> Iterator[None]:
    contact_group_body: dict[str, object] = {"name": _CONTACT_GROUP, "alias": _CONTACT_GROUP}
    # In the ultimatemt edition every config object belongs to a customer,
    # so the field is mandatory here.
    if site.openapi.site_edition.is_ultimatemt_edition():
        contact_group_body["customer"] = "global"
    site.openapi.post(
        "domain-types/contact_group_config/collections/all",
        json=contact_group_body,
    ).raise_for_status()
    site.openapi.hosts.create(
        _VISIBLE_HOST,
        attributes={
            "ipaddress": "127.0.0.1",
            "contactgroups": _contactgroups(_CONTACT_GROUP),
        },
    )
    site.openapi.hosts.create(
        _HIDDEN_HOST,
        attributes={"ipaddress": "127.0.0.1", "contactgroups": _no_contactgroups()},
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        yield
    finally:
        site.openapi.hosts.delete(_VISIBLE_HOST)
        site.openapi.hosts.delete(_HIDDEN_HOST)
        site.openapi.delete(f"/objects/contact_group_config/{_CONTACT_GROUP}")
        site.activate_changes_and_wait_for_core_reload()


@pytest.fixture(name="restricted_user")
def fixture_restricted_user(
    site: Site,
    contact_group_and_hosts: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
) -> Iterator[None]:
    site.openapi.users.create(
        username=_RESTRICTED_USER,
        fullname="Restricted user for CMK-38731",
        password=_RESTRICTED_PASSWORD,
        email=f"{_RESTRICTED_USER}@{site.id}.localhost",
        contactgroups=[_CONTACT_GROUP],
        roles=["user"],
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        yield
    finally:
        site.openapi.users.delete(_RESTRICTED_USER)
        site.activate_changes_and_wait_for_core_reload()


def _list_hosts(site: Site, value: str) -> requests.Response:
    with site.openapi.acting_as(_RESTRICTED_USER, _RESTRICTED_PASSWORD):
        return site.openapi.post(
            "monitor/hosts",
            api_version=APIVersion.INTERNAL,
            json={
                "filter": {"type": "condition", "field": "name", "op": "contains", "value": value}
            },
        )


def test_carriage_return_cannot_bypass_host_visibility(
    site: Site,
    restricted_user: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
) -> None:
    """Pre-fix, the injected payload returned 200 with ``meta.matched == 2``: the blank line it
    smuggled in split the count query in two on the wire, and the half that actually ran against
    Livestatus carried no ``AuthUser`` at all, so it also counted ``_HIDDEN_HOST``. Post-fix, the
    payload is legal input (it carries no "\n"), but every "\r" in it stays inert data on a single
    Livestatus line, so the query still runs under the restricted user's own scoping and matches
    nothing - the payload isn't a real host name.

    The payload also carries the ticket's ``KeepAlive: on`` injection, which relied on the same
    request-splitting bug to reach Livestatus as a header of an unauthenticated second request.
    With the request no longer split, that header never reaches Livestatus at all, so there is
    nothing for a separate assertion to exercise beyond what this one already shows.
    """
    baseline = _list_hosts(site, "h-")
    injected = _list_hosts(site, _CR_INJECTION_PAYLOAD)

    assert baseline.status_code == 200
    assert baseline.json()["meta"]["matched"] == 1

    assert injected.status_code == 200
    assert injected.json()["meta"]["matched"] == 0
