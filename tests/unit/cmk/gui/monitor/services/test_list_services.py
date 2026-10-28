#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.monitor.services._api._list_services import _handle_list_all_services
from cmk.gui.monitor.services._models import HostState, ServiceFilter
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

from .testlib import FakeServicesRepository, ServiceFactory

pytestmark = pytest.mark.usefixtures("request_context")

_URL = "/NO_SITE/check_mk/api/internal/monitor/services"
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def test_handle_list_all_services_returns_host_name_and_site() -> None:
    repo = FakeServicesRepository(
        [ServiceFactory.build(name="CPU load", host_name="web01", site_id="heute")]
    )

    response = _handle_list_all_services(repo, repo.count_total())

    [entry] = response.services
    assert (entry.name, entry.host_name, entry.site_id) == ("CPU load", "web01", "heute")


def test_handle_list_all_services_returns_the_state_of_the_host() -> None:
    repo = FakeServicesRepository([ServiceFactory.build(host_state=HostState.UNREACHABLE)])

    response = _handle_list_all_services(repo, repo.count_total())

    assert [entry.host_state for entry in response.services] == ["UNREACHABLE"]


def test_handle_list_all_services_sorts_by_site_then_host_then_service_by_default() -> None:
    repo = FakeServicesRepository(
        [
            ServiceFactory.build(site_id="remote", host_name="db1", name="CPU"),
            ServiceFactory.build(site_id="central", host_name="web10", name="CPU"),
            ServiceFactory.build(site_id="central", host_name="web9", name="Memory"),
            ServiceFactory.build(site_id="central", host_name="web9", name="CPU"),
        ]
    )

    response = _handle_list_all_services(repo, repo.count_total())

    assert [(s.site_id, s.host_name, s.name) for s in response.services] == [
        ("central", "web9", "CPU"),
        ("central", "web9", "Memory"),
        ("central", "web10", "CPU"),
        ("remote", "db1", "CPU"),
    ]


def test_handle_list_all_services_cuts_the_merged_sites_to_the_limit() -> None:
    repo = FakeServicesRepository(ServiceFactory.batch(10))

    response = _handle_list_all_services(repo, repo.count_total(), limit=7)

    assert len(response.services) == 7
    assert (response.meta.limit, response.meta.matched, response.meta.total) == (7, 10, 10)


def test_handle_list_all_services_reads_the_total_as_matched_when_unfiltered() -> None:
    repo = FakeServicesRepository(ServiceFactory.batch(3))

    _handle_list_all_services(repo, repo.count_total())

    assert repo.count_matched_calls == 0


@pytest.mark.parametrize(
    "query, filters, site_ids",
    [
        pytest.param("web", ServiceFilter(""), None, id="search"),
        pytest.param("", ServiceFilter("Filter: state = 1"), None, id="filter"),
        pytest.param("", ServiceFilter(""), [SiteId("NO_SITE")], id="site scope"),
    ],
)
def test_handle_list_all_services_counts_the_matches_when_narrowed(
    query: str, filters: ServiceFilter, site_ids: list[SiteId] | None
) -> None:
    repo = FakeServicesRepository(ServiceFactory.batch(3), matched=2)

    response = _handle_list_all_services(
        repo, repo.count_total(), query=query, filters=filters, site_ids=site_ids
    )

    assert repo.count_matched_calls == 1
    assert response.meta.matched == 2


@pytest.mark.usefixtures("with_admin_login")
def test_list_all_services_names_a_remote_site_that_does_not_answer(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("services", [])
    mock_livestatus.make_site_unreachable("remote")
    mock_livestatus.expect_query(["GET services", "Stats: state >= 0"], match_type="loose")
    mock_livestatus.expect_query(["GET services"], match_type="loose")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            _URL, params=json.dumps({}), headers=_HEADERS, status=HTTPStatus.OK
        )

    assert resp.json["meta"]["unreachable_sites"] == ["remote"]


@pytest.mark.usefixtures("with_admin_login")
def test_list_all_services_returns_nothing_when_the_filter_excludes_every_site(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(["GET services", "Stats: state >= 0"], match_type="loose")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            _URL,
            params=json.dumps(
                {
                    "filter": {
                        "type": "not",
                        "child": {
                            "type": "condition",
                            "field": "site_id",
                            "op": "one_of",
                            "value": ["NO_SITE"],
                        },
                    }
                }
            ),
            headers=_HEADERS,
            status=HTTPStatus.OK,
        )

    assert resp.json["services"] == []
    assert resp.json["meta"]["matched"] == 0


@pytest.mark.usefixtures("with_admin_login")
def test_list_all_services_rejects_a_site_condition_inside_or(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=False):
        aut_user_auth_wsgi_app.post(
            _URL,
            params=json.dumps(
                {
                    "filter": {
                        "type": "or",
                        "children": [
                            {
                                "type": "condition",
                                "field": "site_id",
                                "op": "one_of",
                                "value": ["NO_SITE"],
                            },
                            {
                                "type": "condition",
                                "field": "host_name",
                                "op": "contains",
                                "value": "web",
                            },
                        ],
                    }
                }
            ),
            headers=_HEADERS,
            status=HTTPStatus.BAD_REQUEST,
        )


@pytest.mark.usefixtures("with_admin_login")
def test_list_all_services_rejects_a_site_that_does_not_exist(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=False):
        resp = aut_user_auth_wsgi_app.post(
            _URL,
            params=json.dumps(
                {
                    "filter": {
                        "type": "condition",
                        "field": "site_id",
                        "op": "one_of",
                        "value": ["gone"],
                    }
                }
            ),
            headers=_HEADERS,
            status=HTTPStatus.BAD_REQUEST,
        )

    assert resp.json["detail"] == "Site 'gone' does not exist."
