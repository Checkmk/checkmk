#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

import cmk.utils.paths
from cmk.gui.monitor.services._api._list_host_services import _handle_list_services
from cmk.gui.monitor.services._models import (
    ServiceFilter,
    ServiceSort,
    ServiceSortColumn,
    ServiceSortDirection,
    ServiceState,
)
from cmk.gui.openapi.utils import ProblemException
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.setup_git_test_helper import (
    init_setup_git_repo,
    setup_git_commit_subjects,
)
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK

from .testlib import get_fake_host_services_repository, KNOWN_HOSTNAME, ServiceFactory

# Building the response entries renders each service's Perf-O-Meter, which reaches into the
# request-scoped configuration, user and theme.
pytestmark = pytest.mark.usefixtures("request_context")

_SITE_ID = "local"


def test_handle_list_services_limit_handling() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    response = _handle_list_services(
        services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID, limit=7
    )

    assert len(response.services) == 7
    assert response.meta.limit == 7
    assert response.meta.matched == 10
    assert response.meta.total == 10


def test_handle_list_services_without_limit_returns_all() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    response = _handle_list_services(
        services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID, limit=None
    )

    assert len(response.services) == 10
    assert response.meta.limit is None
    assert response.meta.matched == 10
    assert response.meta.total == 10


def test_handle_list_services_state_label_conversion() -> None:
    services_repo = get_fake_host_services_repository(n_services=100)
    response = _handle_list_services(services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID)
    service_states = [service.state for service in response.services]

    assert all(state in {"OK", "WARN", "CRIT", "UNKNOWN", "PENDING"} for state in service_states)


def test_handle_list_services_pending_state_round_trips() -> None:
    services = [
        ServiceFactory.build(name="Pending service", state=ServiceState.PENDING),
        ServiceFactory.build(name="Checked service", state=ServiceState.OK),
    ]
    services_repo = get_fake_host_services_repository(services=services)
    response = _handle_list_services(services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID)

    state_by_name = {service.name: service.state for service in response.services}
    assert state_by_name == {"Pending service": "PENDING", "Checked service": "OK"}


def test_handle_list_services_meta_round_trips_hostname_and_site() -> None:
    services_repo = get_fake_host_services_repository(n_services=1)
    response = _handle_list_services(services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID)

    assert response.meta.hostname == KNOWN_HOSTNAME
    assert response.meta.site_id == _SITE_ID


def test_handle_list_services_forwards_requested_sort() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    ascending = _handle_list_services(
        services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID, limit=None
    )
    descending = _handle_list_services(
        services_repo,
        hostname=KNOWN_HOSTNAME,
        site_id=_SITE_ID,
        limit=None,
        sorters=[ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.DESC)],
    )

    assert [service.name for service in descending.services] == list(
        reversed([service.name for service in ascending.services])
    )


def test_handle_list_services_defaults_to_the_legacy_service_order() -> None:
    """Without a requested sort the page must show Checkmk's own services first, as legacy does."""
    names = ["Memory", "Check_MK Discovery", "APT Updates", "Check_MK"]
    services_repo = get_fake_host_services_repository(n_services=len(names), names=names)

    response = _handle_list_services(
        services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID, limit=None
    )

    assert [service.name for service in response.services] == [
        "Check_MK",
        "Check_MK Discovery",
        "APT Updates",
        "Memory",
    ]


def test_handle_list_services_takes_a_requested_name_sort_literally() -> None:
    """An explicitly requested name sort is plain alphabetical, unlike the page default."""
    names = ["Memory", "Check_MK Discovery", "APT Updates", "Check_MK"]
    services_repo = get_fake_host_services_repository(n_services=len(names), names=names)

    response = _handle_list_services(
        services_repo,
        hostname=KNOWN_HOSTNAME,
        site_id=_SITE_ID,
        limit=None,
        sorters=[ServiceSort(column=ServiceSortColumn.NAME, direction=ServiceSortDirection.ASC)],
    )

    assert [service.name for service in response.services] == [
        "APT Updates",
        "Check_MK",
        "Check_MK Discovery",
        "Memory",
    ]


def test_handle_list_services_filters_by_search_query() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    items = services_repo.fetch(
        KNOWN_HOSTNAME,
        limit=1,
        query="",
        sorters=[],
        filters=ServiceFilter(""),
        fields=frozenset(),
    )
    known_name = items[0].name

    response = _handle_list_services(
        services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID, query=known_name
    )

    assert response.meta.matched == len(response.services)
    assert response.meta.matched >= 1
    assert all(known_name.lower() in service.name.lower() for service in response.services)


def test_handle_list_services_empty_query_matches_all() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    response = _handle_list_services(services_repo, hostname=KNOWN_HOSTNAME, site_id=_SITE_ID)

    assert response.meta.matched == 10
    assert response.meta.total == 10


def test_handle_list_services_host_not_found() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    with pytest.raises(ProblemException, match="404"):
        _handle_list_services(services_repo, hostname="unknown-host", site_id=_SITE_ID)


@pytest.mark.usefixtures("with_admin_login")
def test_list_host_services_does_not_commit_the_setup_git_repo(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    config_dir = cmk.utils.paths.default_config_dir
    init_setup_git_repo(config_dir)
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("hosts", [{"name": "heute"}])
    mock_livestatus.add_table("services", [])
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = heute\nLimit: 1")
    mock_livestatus.expect_query(["GET services"], match_type="loose")
    mock_livestatus.expect_query(["GET services", "Stats: state >= 0"], match_type="loose")

    with set_config(wato_use_git=True), mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/heute/services?site_id=NO_SITE",
            params=json.dumps({}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == 200, resp.text
    assert setup_git_commit_subjects(config_dir) == ["Initialized GIT for Checkmk"]
