#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteConfiguration

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.openapi.framework import APIVersion
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.gui.web_test_app import SetConfig
from tests.testlib.rest_api_client import ClientRegistry

_COLLECTION_URL = "/domain-types/livestatus_query/collections/all"


def _site_configs(site_ids: list[SiteId]) -> dict[SiteId, SiteConfiguration]:
    return {
        site_id: SiteConfiguration(
            id=site_id,
            alias=str(site_id),
            socket=("local", None),
            disable_wato=True,
            disabled=False,
            insecure=False,
            url_prefix=f"/{site_id}/",
            multisiteurl="",
            persist=False,
            replicate_ec=False,
            replicate_mkps=False,
            replication=None,
            timeout=5,
            user_login=True,
            proxy=None,
            user_attribute_sync_connections="all",
            status_host=None,
            message_broker_port=5672,
            is_trusted=False,
        )
        for site_id in site_ids
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_query_endpoint_returns_rows(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live = mock_livestatus
    live.add_table("hosts", [{"name": "heute", "alias": "heute"}])
    # "Limit: 1000" is the endpoint's default row cap; every query carries one.
    live.expect_query(["GET hosts", "Columns: name alias", "Filter: alias ~ heute", "Limit: 1000"])
    with live:
        resp = clients.LivestatusQuery.query(
            "hosts",
            ["name", "alias"],
            query={"op": "~", "left": "alias", "right": "heute"},
        )
    assert resp.status_code == 200
    assert resp.json["table"] == "hosts", resp.json
    assert resp.json["columns"] == ["name", "alias"], resp.json
    assert resp.json["rows"] == [{"name": "heute", "alias": "heute"}], resp.json
    # No restful-objects envelope keys leak in: the exact flat contract cmk-mcp parses.
    assert set(resp.json) == {"table", "columns", "rows"}, resp.json


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_row_keys_match_the_echoed_columns_for_a_renamed_column(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """`log.class_` is the one exposed column whose attribute name differs from its wire name.

    The request names it `class_` (that is what column validation accepts), livestatus is asked
    for `class`, and the response has to stay internally consistent: whatever `columns` echoes
    must be the key present in every row.
    """
    live = mock_livestatus
    live.add_table("log", [{"class": 1, "message": "a log message"}])
    live.expect_query(["GET log", "Columns: class message", "Limit: 1000"])
    with live:
        resp = clients.LivestatusQuery.query("log", ["class_", "message"])
    assert resp.status_code == 200
    assert resp.json["columns"] == ["class_", "message"], resp.json
    assert resp.json["rows"] == [{"class_": 1, "message": "a log message"}], resp.json


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_explicit_limit_reaches_livestatus(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live = mock_livestatus
    live.add_table("hosts", [{"name": "heute"}])
    live.expect_query(["GET hosts", "Columns: name", "Limit: 5"])
    with live:
        resp = clients.LivestatusQuery.query("hosts", ["name"], limit=5)
    assert resp.status_code == 200


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_sites_restricts_query_to_named_site(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    with set_config(sites=_site_configs([SiteId("NO_SITE"), SiteId("remote")])):
        live = mock_livestatus
        live.set_sites(["NO_SITE", "remote"])
        live.add_table("hosts", [{"name": "local_host"}], site="NO_SITE")
        live.add_table("hosts", [{"name": "remote_host"}], site="remote")
        # only_sites must restrict the data query to NO_SITE; expecting it on that
        # site alone fails the test if the query also reaches the remote site.
        live.expect_query(["GET hosts", "Columns: name", "Limit: 1000"], sites=["NO_SITE"])
        with live:
            resp = clients.LivestatusQuery.query("hosts", ["name"], sites=["NO_SITE"])
        assert resp.status_code == 200
        assert resp.json["rows"] == [{"name": "local_host"}], (
            f"only NO_SITE's rows should be returned, got {resp.json['rows']}"
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            {"table": "statehist", "columns": ["name"]},
            id="unregistered-table",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["name\nColumnHeaders: on"]},
            id="newline-column",
        ),
        pytest.param(
            {
                "table": "hosts",
                "columns": ["name"],
                "query": {"op": "=", "left": "services.description", "right": "x"},
            },
            id="foreign-table-filter",
        ),
        pytest.param(
            {"table": "hosts", "columns": ["name"], "output_format": "python"},
            id="unknown-body-field",
        ),
    ],
)
def test_rejected_bodies_never_reach_livestatus(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    body: dict[str, object],
) -> None:
    live = mock_livestatus
    # Enter with no expected queries: validation must complete before any livestatus I/O,
    # so any emitted query fails the test.
    with live(expect_status_query=False):
        resp = clients.LivestatusQuery.request(
            "post", url=_COLLECTION_URL, body=body, expect_ok=False
        )
    assert resp.status_code == 400, (
        f"body {body!r} should be rejected with 400, got {resp.status_code}"
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_endpoint_reachable_only_under_internal_version(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    live = mock_livestatus
    live.add_table("hosts", [{"name": "heute"}])

    # Under the public /1.0/ namespace the internal-tier endpoint is not registered.
    with live(expect_status_query=False):
        resp = clients.LivestatusQuery.query(
            "hosts", ["name"], api_version=APIVersion.V1, expect_ok=False
        )
    assert resp.status_code == 404, (
        f"internal endpoint must not appear under the public version, got {resp.status_code}"
    )

    # expect_status_query is stateful on the mock and was set False above, so ask for the
    # connection-setup status query explicitly here rather than relying on the default.
    live.expect_query(["GET hosts", "Columns: name", "Limit: 1000"])
    with live(expect_status_query=True):
        resp = clients.LivestatusQuery.query("hosts", ["name"])
    assert resp.status_code == 200


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_query_carries_authuser_for_non_see_all_user(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    username, password = with_user
    clients.LivestatusQuery.set_credentials(username, password)
    live = mock_livestatus
    live.add_table("hosts", [{"name": "heute"}])
    # A see_all-less user makes sites.live() attach an AuthUser header; a missing
    # AuthUser line fails the loose match, flagging a row-scoping regression.
    live.expect_query(
        ["GET hosts", "Columns: name", f"AuthUser: {username}"],
        match_type="loose",
    )
    with live:
        resp = clients.LivestatusQuery.query("hosts", ["name"])
    assert resp.status_code == 200
