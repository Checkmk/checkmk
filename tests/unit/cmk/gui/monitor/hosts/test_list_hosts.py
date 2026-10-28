#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus

import pytest

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.monitor.hosts._api._filters import SiteScopedFilter
from cmk.gui.monitor.hosts._api._list_hosts import _handle_list_hosts
from cmk.gui.monitor.hosts._models import HostOptionalField
from cmk.gui.monitor.hosts.table import HostTable, InvalidFilterError, MonitorFolders
from cmk.gui.monitor.shared import AndNode, HostState, NumericCondition, StringCondition
from cmk.gui.openapi.framework.model import ApiOmitted
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


def test_handle_list_hosts_links_a_host_with_graphs_to_its_graphs_page() -> None:
    hosts = [HostFactory.build(name="web-1", site_id="local", has_graphs=True)]
    host_repo = get_fake_host_repository(hosts=hosts)
    response = _handle_list_hosts(
        host_repo, host_repo.count_total(), fields=frozenset({HostOptionalField.GRAPHS_LINK})
    )

    assert [host.graphs_link for host in response.hosts] == [
        "view.py?view_name=host_graphs&site=local&host=web-1"
    ]


def test_handle_list_hosts_omits_the_graphs_link_of_a_host_without_graphs() -> None:
    hosts = [HostFactory.build(has_graphs=False)]
    host_repo = get_fake_host_repository(hosts=hosts)
    response = _handle_list_hosts(
        host_repo, host_repo.count_total(), fields=frozenset({HostOptionalField.GRAPHS_LINK})
    )

    assert [host.graphs_link for host in response.hosts] == [ApiOmitted()]


def test_handle_list_hosts_omits_the_graphs_link_when_not_asked_for() -> None:
    hosts = [HostFactory.build(has_graphs=True)]
    host_repo = get_fake_host_repository(hosts=hosts)
    response = _handle_list_hosts(host_repo, host_repo.count_total(), fields=frozenset())

    assert [host.graphs_link for host in response.hosts] == [ApiOmitted()]


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

    assert resp.status_code == HTTPStatus.OK, resp.text
    assert setup_git_commit_subjects(config_dir) == ["Initialized GIT for Checkmk"]


def test_handle_list_hosts_keeps_a_hidden_service_count_column_independent() -> None:
    """A count field that wasn't asked for must be omitted without blanking out the others."""
    hosts = [HostFactory.build(num_services_ok=5, num_services=None)]
    host_repo = get_fake_host_repository(hosts=hosts)

    response = _handle_list_hosts(
        host_repo,
        host_repo.count_total(),
        fields=frozenset({HostOptionalField.NUM_SERVICES_OK}),
    )

    host = response.hosts[0]
    assert host.num_services_ok == 5
    assert isinstance(host.num_services, ApiOmitted)


@pytest.mark.usefixtures("with_admin_login")
def test_list_hosts_names_a_remote_site_that_does_not_answer(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("hosts", [])
    mock_livestatus.make_site_unreachable("remote")
    mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
    mock_livestatus.expect_query(["GET hosts"], match_type="loose")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts",
            params=json.dumps({}),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.OK,
        )

    assert resp.json["meta"]["unreachable_sites"] == ["remote"]


@pytest.mark.usefixtures("with_admin_login")
def test_list_hosts_returns_no_hosts_when_the_filter_excludes_every_site(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")

    with mock_livestatus:
        resp = aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts",
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
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.OK,
        )

    assert resp.json["hosts"] == []
    assert resp.json["meta"]["matched"] == 0


@pytest.mark.usefixtures("with_admin_login")
def test_list_hosts_rejects_a_site_condition_inside_or_without_querying_livestatus(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus(expect_status_query=False):
        aut_user_auth_wsgi_app.post(
            "/NO_SITE/check_mk/api/internal/monitor/hosts",
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
                                "field": "name",
                                "op": "contains",
                                "value": "web",
                            },
                        ],
                    }
                }
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            status=HTTPStatus.BAD_REQUEST,
        )


def test_handle_list_hosts_reports_no_timestamps_for_a_pending_host() -> None:
    hosts = [
        HostFactory.build(name="pending-host", last_check=0, last_state_change=0),
        HostFactory.build(name="checked-host", last_check=1752405510, last_state_change=1752405540),
    ]
    host_repo = get_fake_host_repository(hosts=hosts)

    response = _handle_list_hosts(
        host_repo,
        host_repo.count_total(),
        fields=frozenset({HostOptionalField.LAST_CHECK, HostOptionalField.LAST_STATE_CHANGE}),
    )

    timestamps = {host.name: (host.last_check, host.last_state_change) for host in response.hosts}
    assert timestamps == {
        "pending-host": (None, None),
        "checked-host": (1752405510, 1752405540),
    }


def test_handle_list_hosts_omits_timestamps_that_were_not_asked_for() -> None:
    host_repo = get_fake_host_repository(hosts=[HostFactory.build(last_check=0)])

    response = _handle_list_hosts(host_repo, host_repo.count_total(), fields=frozenset())

    assert isinstance(response.hosts[0].last_check, ApiOmitted)


def _host_table() -> HostTable:
    return HostTable(active_config.sites, MonitorFolders())


@pytest.mark.parametrize(
    "site_condition, exclude_sites",
    [
        pytest.param(
            {"type": "condition", "field": "site_id", "op": "one_of", "value": ["NO_SITE"]},
            False,
            id="site",
        ),
        pytest.param(
            {
                "type": "not",
                "child": {
                    "type": "condition",
                    "field": "site_id",
                    "op": "one_of",
                    "value": ["NO_SITE"],
                },
            },
            True,
            id="negated site",
        ),
    ],
)
def test_a_filter_tree_from_the_page_url_parses_into_site_scoped_filter_nodes(
    site_condition: dict[str, object], exclude_sites: bool
) -> None:
    raw = json.dumps(
        {
            "type": "and",
            "children": [
                {"type": "condition", "field": "name", "op": "contains", "value": "web"},
                {"type": "condition", "field": "num_services", "op": "gt", "value": 3},
                site_condition,
            ],
        }
    )

    scoped = _host_table().parse_filter(raw)

    assert scoped == SiteScopedFilter(
        node=AndNode(
            type="and",
            children=[
                StringCondition(type="condition", field="name", op="contains", value="web"),
                NumericCondition(type="condition", field="num_services", op="gt", value=3),
            ],
        ),
        sites=frozenset({SiteId("NO_SITE")}),
        exclude_sites=exclude_sites,
    )


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("{not json", id="malformed JSON"),
        pytest.param(
            '{"type": "condition", "field": "no_such_field", "op": "eq", "value": 1}',
            id="unknown field",
        ),
        pytest.param('{"type": "and", "children": []}', id="AND without children"),
        pytest.param(
            json.dumps(
                {
                    "type": "or",
                    "children": [
                        {
                            "type": "condition",
                            "field": "site_id",
                            "op": "one_of",
                            "value": ["remote"],
                        },
                        {"type": "condition", "field": "name", "op": "contains", "value": "web"},
                    ],
                }
            ),
            id="site condition under OR",
        ),
        pytest.param(
            '{"type": "condition", "field": "site_id", "op": "one_of", "value": ["ghost"]}',
            id="unknown site",
        ),
    ],
)
def test_an_invalid_filter_tree_is_rejected_as_invalid_filter(raw: str) -> None:
    with pytest.raises(InvalidFilterError):
        _host_table().parse_filter(raw)


def _listed_host(name: str, *, alias: str = "", address: str = "") -> dict[str, object]:
    return {
        "name": name,
        "alias": alias or name,
        "address": address or "127.0.0.1",
        "state": 0,
        "has_been_checked": 1,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "comments": [],
        "modified_attributes_list": [],
        "active_checks_enabled": 1,
        "accept_passive_checks": 1,
        "in_notification_period": 1,
        "in_service_period": 1,
        "in_check_period": 1,
        "is_flapping": 0,
        "staleness": 0.0,
        "filename": "",
        "labels": {},
        "label_sources": {},
        "label_names": [],
        "label_values": [],
        "tags": {},
        "tag_names": [],
        "tag_values": [],
        "contacts": [],
        "contact_groups": [],
        "groups": [],
    }


def _only_host_named(
    mock_livestatus: MockLiveStatusConnection, hosts: list[dict[str, object]], search: str
) -> str | None:
    mock_livestatus.add_table("hosts", hosts)
    mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
    mock_livestatus.expect_query(["GET hosts"], match_type="loose")
    mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
    with mock_livestatus:
        host = _host_table().only_host(query=search, filter_node=None)
    return None if host is None else host.name


def test_only_host_is_the_single_host_the_search_finds(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    assert (
        _only_host_named(mock_livestatus, [_listed_host("web01"), _listed_host("db01")], "web")
        == "web01"
    )


@pytest.mark.parametrize(
    "other_host",
    [
        pytest.param(_listed_host("proxy01", alias="web proxy"), id="by-alias"),
        pytest.param(_listed_host("proxy01", address="web.example.com"), id="by-address"),
    ],
)
def test_only_host_is_none_when_the_search_finds_another_host_by_a_searched_column(
    mock_livestatus: MockLiveStatusConnection, other_host: dict[str, object]
) -> None:
    assert _only_host_named(mock_livestatus, [_listed_host("web01"), other_host], "web") is None
