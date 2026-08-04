#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.monitor.services._api._list_host_services import _handle_list_services
from cmk.gui.monitor.services._models import ServiceSort, ServiceSortColumn, ServiceSortDirection
from cmk.gui.openapi.utils import ProblemException

from .testlib import get_fake_host_services_repository, KNOWN_HOSTNAME

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

    assert all(state in {"OK", "WARN", "CRIT", "UNKN"} for state in service_states)


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


def test_handle_list_services_filters_by_search_query() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    known_name = services_repo.fetch(KNOWN_HOSTNAME, limit=1, query="", sorters=[])[0].name

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
