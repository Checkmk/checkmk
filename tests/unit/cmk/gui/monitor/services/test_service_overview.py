#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.monitor.services._api._list_host_services import _handle_list_services
from cmk.gui.monitor.services._api._service_overview import _handle_get_service_overview
from cmk.gui.openapi.utils import ProblemException

from .testlib import get_fake_host_services_repository, KNOWN_HOSTNAME, KNOWN_SITE_ID

# Building the response entries renders each service's Perf-O-Meter, which reaches into the
# request-scoped configuration, user and theme.
pytestmark = pytest.mark.usefixtures("request_context")


def test_get_service_overview_success() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    response = _handle_list_services(services_repo, hostname=KNOWN_HOSTNAME, site_id=KNOWN_SITE_ID)
    service = response.services[0]

    fetched_service = _handle_get_service_overview(
        services_repo,
        hostname=KNOWN_HOSTNAME,
        service_name=service.name,
        site_id=KNOWN_SITE_ID,
    )

    assert fetched_service.name == service.name
    assert fetched_service.host_name == KNOWN_HOSTNAME
    assert fetched_service.site_id == KNOWN_SITE_ID


def test_get_service_overview_unknown_service() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    with pytest.raises(ProblemException, match="404"):
        _handle_get_service_overview(
            services_repo,
            hostname=KNOWN_HOSTNAME,
            service_name="not-a-service",
            site_id=KNOWN_SITE_ID,
        )


def test_get_service_overview_unknown_host() -> None:
    services_repo = get_fake_host_services_repository(n_services=10)
    with pytest.raises(ProblemException, match="404"):
        _handle_get_service_overview(
            services_repo,
            hostname="not-a-host",
            service_name="whatever",
            site_id=KNOWN_SITE_ID,
        )
