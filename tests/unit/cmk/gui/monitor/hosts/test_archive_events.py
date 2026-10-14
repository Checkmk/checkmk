#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.monitor.hosts._api._archive_events import (
    _handle_archive_events,
    ArchiveEventsHostRef,
    ArchiveEventsRequestBody,
)
from cmk.gui.monitor.hosts._models import HostTarget
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK


class _FakeHostEventArchiver:
    def __init__(self) -> None:
        self.calls: list[tuple[list[HostTarget], UserId]] = []

    def archive_events(self, targets: Sequence[HostTarget], *, author: UserId) -> int:
        self.calls.append((list(targets), author))
        return len(targets)


def test_archives_the_events_of_each_host_once() -> None:
    archiver = _FakeHostEventArchiver()
    body = ArchiveEventsRequestBody(
        hosts=[
            ArchiveEventsHostRef(site_id="local", name="web-01"),
            ArchiveEventsHostRef(site_id="local", name="web-01"),
            ArchiveEventsHostRef(site_id="remote", name="web-01"),
        ]
    )

    response = _handle_archive_events(archiver, body, author=UserId("harry"))

    assert response.archived == 2
    assert archiver.calls == [
        ([HostTarget("local", "web-01"), HostTarget("remote", "web-01")], UserId("harry"))
    ]


def test_no_hosts_archive_nothing() -> None:
    archiver = _FakeHostEventArchiver()

    response = _handle_archive_events(
        archiver, ArchiveEventsRequestBody(hosts=[]), author=UserId("harry")
    )

    assert (response.archived, archiver.calls) == (0, [])


@pytest.mark.usefixtures("with_admin_login")
def test_sends_the_archiving_to_the_site_of_the_host(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name\nFilter: name = heute", sites=["NO_SITE"]
    )
    mock_livestatus.expect_query(
        "COMMAND [...] EC_DELETE_EVENTS_OF_HOST;heute;...", match_type="ellipsis"
    )

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/archive_events",
            params=json.dumps({"hosts": [{"site_id": "NO_SITE", "name": "heute"}]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert resp.json == {"archived": 1}


@pytest.mark.usefixtures("with_admin_login")
def test_refuses_a_user_without_the_permission_to_archive_events(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
    load_config: Config,
) -> None:
    roles = copy.deepcopy(load_config.roles)
    roles["admin"]["permissions"] = {
        **roles["admin"].get("permissions", {}),
        "mkeventd.archive_events_of_hosts": False,
    }

    with set_config(roles=roles), mock_livestatus(expect_status_query=False):
        aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts/actions/archive_events",
            params=json.dumps({"hosts": [{"site_id": "NO_SITE", "name": "heute"}]}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.FORBIDDEN,
        )
