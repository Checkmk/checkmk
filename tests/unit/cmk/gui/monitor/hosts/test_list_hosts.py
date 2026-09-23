#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest

import cmk.utils.paths
from cmk.gui.monitor.hosts._api._list_hosts import _handle_list_hosts
from cmk.gui.monitor.hosts._models import HostState
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.setup_git_test_helper import (
    init_setup_git_repo,
    setup_git_commit_subjects,
)
from tests.testlib.unit.gui.web_test_app import SetConfig, WebTestAppForCMK

from .testlib import get_fake_host_repository, HostFactory

pytestmark = pytest.mark.usefixtures("request_context")


def test_handle_list_hosts_limit_handling() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, host_repo.count_total(), limit=7)

    assert len(response.hosts) == 7
    assert response.meta.limit == 7
    assert response.meta.total == 10
    assert response.meta.matched == 10


def test_handle_list_hosts_without_limit_returns_all() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, host_repo.count_total(), limit=None)

    assert len(response.hosts) == 10
    assert response.meta.limit is None
    assert response.meta.total == 10
    assert response.meta.matched == 10


def test_handle_list_hosts_state_label_conversion() -> None:
    host_repo = get_fake_host_repository(n_hosts=100)
    response = _handle_list_hosts(host_repo, host_repo.count_total())
    host_states = [host.state for host in response.hosts]

    assert all(state in {"UP", "DOWN", "UNREACHABLE", "PENDING"} for state in host_states)


def test_handle_list_hosts_pending_state_round_trips() -> None:
    hosts = [
        HostFactory.build(name="pending-host", state=HostState.PENDING),
        HostFactory.build(name="checked-host", state=HostState.UP),
    ]
    host_repo = get_fake_host_repository(hosts=hosts)
    response = _handle_list_hosts(host_repo, host_repo.count_total())

    state_by_name = {host.name: host.state for host in response.hosts}
    assert state_by_name == {"pending-host": "PENDING", "checked-host": "UP"}


@pytest.mark.usefixtures("with_admin_login")
def test_list_hosts_does_not_commit_the_setup_git_repo(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    config_dir = cmk.utils.paths.default_config_dir
    init_setup_git_repo(config_dir)
    mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
    mock_livestatus.expect_query(["GET hosts"], match_type="loose")

    with set_config(wato_use_git=True), mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts",
            params=json.dumps({}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    assert resp.status_code == 200, resp.text
    assert setup_git_commit_subjects(config_dir) == ["Initialized GIT for Checkmk"]
