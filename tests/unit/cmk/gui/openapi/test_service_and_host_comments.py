#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import random
import time
from typing import Any

import pytest
from faker import Faker

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from tests.testlib.unit.rest_api_client import ClientRegistry

DOMAIN_TYPE = "comment"
SITE_ID = "NO_SITE"


def add_service_and_host_comments_to_live_status_table(live: MockLiveStatusConnection) -> None:
    f = Faker()

    def create_comment(comment_id: int, service_comment: bool) -> dict[str, Any]:
        return {
            "host_name": "heute",
            "id": comment_id,
            "author": f.first_name(),
            "comment": f.text(max_nb_chars=30),
            "persistent": random.choice((0, 1)),
            "entry_time": time.time() - random.randint(10**5, 10**9),
            "service_description": f"service_{comment_id}" if service_comment else "",
            "is_service": 1 if service_comment else 0,
        }

    live.add_table(
        "comments",
        [create_comment(1, service_comment=False), create_comment(2, service_comment=True)],
    )
    live.add_table("hosts", [{"name": "heute"}])
    live.add_table("services", [{"description": "service1", "host_name": "heute"}])


def test_get_all_comments(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service"
    )
    with mock_livestatus:
        resp = clients.Comment.get_all()
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert resp.json["value"][0]["extensions"]["site_id"] == SITE_ID


def test_get_host_comments(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 0"
    )
    with mock_livestatus:
        clients.Comment.get_host()


def test_get_service_comments(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 1"
    )
    with mock_livestatus:
        clients.Comment.get_service()


def test_get_comments_that_dont_exist(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = non_existing_host\nFilter: service_description = non_existing_service\nAnd: 2"
    )
    with mock_livestatus:
        resp = clients.Comment.get_all(
            host_name="non_existing_host",
            service_description="non_existing_service",
            expect_ok=False,
        )
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["extensions"] == {}


def test_comment_params_execption(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    with mock_livestatus:
        resp = clients.Comment.get_host(
            host_name="heute", service_description="service_1", expect_ok=False
        ).assert_status_code(400)
    assert resp.json["title"] == "Invalid parameter combination"
    assert (
        resp.json["detail"]
        == "You set collection_name to host but the provided filtering parameters will return only service comments."
    )


def test_get_non_existing_comment(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: host_name id author comment persistent service_description entry_time is_service",
            "Filter: id = 100",
        ],
        sites=[SITE_ID],
    )
    with mock_livestatus:
        clients.Comment.get(comment_id=100, site_id=SITE_ID, expect_ok=False).assert_status_code(
            404
        )


def test_get_comment_invalid_id(clients: ClientRegistry) -> None:
    resp = clients.Comment.get(
        comment_id="invalid_id", site_id=SITE_ID, expect_ok=False
    ).assert_status_code(404)
    assert resp.json["title"] == "Not Found"
    assert resp.json["detail"] == "These fields have problems: comment_id"


def test_get_host_comment_by_id(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: host_name id author comment persistent service_description entry_time is_service",
            "Filter: id = 1",
        ],
        sites=[SITE_ID],
    )

    with mock_livestatus:
        resp = clients.Comment.get(comment_id=1, site_id=SITE_ID)
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert {link["method"] for link in resp.json["links"]} == {"GET", "DELETE"}
        assert set((resp.json["extensions"]).keys()) == {
            "host_name",
            "id",
            "author",
            "comment",
            "persistent",
            "entry_time",
            "is_service",
            "site_id",
        }


def test_get_service_comment_by_id(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: host_name id author comment persistent service_description entry_time is_service",
            "Filter: id = 2",
        ],
        sites=[SITE_ID],
    )
    with mock_livestatus:
        resp = clients.Comment.get(comment_id=2, site_id=SITE_ID)
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert {link["method"] for link in resp.json["links"]} == {"GET", "DELETE"}
        assert set((resp.json["extensions"]).keys()) == {
            "host_name",
            "id",
            "author",
            "comment",
            "persistent",
            "entry_time",
            "service_description",
            "is_service",
            "site_id",
        }


def test_get_all_host_comments(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 0"
    )
    with mock_livestatus:
        resp = clients.Comment.get_host()
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert set(resp.json["value"][0]["extensions"].keys()) == {
            "host_name",
            "id",
            "author",
            "comment",
            "persistent",
            "entry_time",
            "is_service",
            "site_id",
        }


def test_get_host_comments_by_query(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = heute"
    )
    with mock_livestatus:
        resp = clients.Comment.get_all(
            query='{"op": "=", "left": "comments.host_name", "right": "heute"}'
        )
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert resp.json["value"][0]["extensions"]["host_name"] == "heute"


def test_get_all_service_comments(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 1"
    )
    with mock_livestatus:
        resp = clients.Comment.get_service()
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert set(resp.json["value"][0]["extensions"].keys()) == {
            "host_name",
            "id",
            "author",
            "comment",
            "persistent",
            "entry_time",
            "service_description",
            "is_service",
            "site_id",
        }


def test_get_service_comments_by_query(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 1"
    )
    with mock_livestatus:
        resp = clients.Comment.get_all(
            query='{"op": "=", "left": "comments.is_service", "right": "1"}'
        )

        assert resp.json["domainType"] == DOMAIN_TYPE


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_post_host_comment(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    post_params = {
        "comment_type": "host",
        "host_name": "heute",
        "comment": "This is a test comment",
    }
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    mock_livestatus.expect_query(
        f"COMMAND [...] ADD_HOST_COMMENT;{post_params['host_name']};0;test123-...;{post_params['comment']}",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Comment.create_for_host(
            comment=post_params["comment"], comment_type="host", host_name=post_params["host_name"]
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_post_service_comment(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    post_params = {
        "comment_type": "service",
        "host_name": "heute",
        "comment": "This is a test comment",
        "service_description": "service1",
    }
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    mock_livestatus.expect_query(
        f"COMMAND [...] ADD_SVC_COMMENT;{post_params['host_name']};{post_params['service_description']};0;test123-...;{post_params['comment']}",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Comment.create_for_service(
            comment=post_params["comment"],
            host_name=post_params["host_name"],
            service_description=post_params["service_description"],
            comment_type="service",
        )


def test_post_host_comment_with_query(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    comment = "This is a test comment"

    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    mock_livestatus.expect_query(
        f"COMMAND [...] ADD_HOST_COMMENT;heute;0;test123-...;{comment}",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Comment.create_for_host(
            comment_type="host_by_query",
            comment=comment,
            query={"op": "=", "left": "hosts.name", "right": "heute"},
        )


def test_post_service_comment_with_query(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)

    comment = "This is a test comment"

    mock_livestatus.expect_query(
        "GET services\nColumns: description host_name\nFilter: description = service1\nFilter: host_name = heute\nAnd: 2"
    )
    mock_livestatus.expect_query(
        f"COMMAND [...] ADD_SVC_COMMENT;heute;service1;1;test123-...;{comment}",
        match_type="ellipsis",
    )
    with mock_livestatus:
        clients.Comment.create_for_service(
            comment_type="service_by_query",
            comment=comment,
            query={
                "op": "and",
                "expr": [
                    {
                        "op": "=",
                        "left": "services.description",
                        "right": "service1",
                    },
                    {"op": "=", "left": "services.host_name", "right": "heute"},
                ],
            },
            persistent=True,
        )


def test_post_service_comment_invalid_query(clients: ClientRegistry) -> None:
    resp = clients.Comment.create_for_service(
        comment="This is a test comment",
        comment_type="service_by_query",
        query="something that is not a query",
        expect_ok=False,
    )

    assert resp.json["detail"] == "These fields have problems: query"


def test_post_host_comment_invalid_query(clients: ClientRegistry) -> None:
    resp = clients.Comment.create_for_host(
        comment="This is a test comment",
        comment_type="host_by_query",
        query="something that is not a query",
        expect_ok=False,
    )
    assert resp.json["detail"] == "These fields have problems: query"


def test_post_service_comment_invalid_comment_type(clients: ClientRegistry) -> None:
    comment_type = "this should not work"

    resp = clients.Comment.create_for_service(
        comment_type=comment_type, comment="This is a test comment", expect_ok=False
    )
    assert resp.json["detail"] == "These fields have problems: comment_type"
    assert resp.json["fields"]["comment_type"][0] == f"Unsupported value: {comment_type}"


def test_post_host_comment_invalid_comment_type(clients: ClientRegistry) -> None:
    comment_type = "this should not work"

    resp = clients.Comment.create_for_host(
        comment_type=comment_type, comment="This is a test comment", expect_ok=False
    )
    assert resp.json["detail"] == "These fields have problems: comment_type"
    assert resp.json["fields"]["comment_type"][0] == f"Unsupported value: {comment_type}"


def test_delete_comment_by_id(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: id is_service",
            "Filter: id = 1",
        ],
        sites=["NO_SITE"],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_COMMENT;1", match_type="ellipsis")
    with mock_livestatus:
        clients.Comment.delete(delete_type="by_id", comment_id=1, site_id=SITE_ID)


def test_delete_invalid_comment_ids(clients: ClientRegistry) -> None:
    for bad_int in [True, False, "abc"]:
        resp = clients.Comment.delete(
            delete_type="by_id", comment_id=bad_int, site_id=SITE_ID, expect_ok=False
        ).assert_status_code(400)
        assert resp.json["title"] == "Bad Request"
        assert resp.json["detail"] == "These fields have problems: comment_id"
        assert resp.json["fields"]["comment_id"][0] == "Not a valid integer."


def test_delete_comments_by_query(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: id is_service",
            "Filter: host_name = heute",
        ],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_COMMENT;1", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_COMMENT;2", match_type="ellipsis")

    with mock_livestatus:
        clients.Comment.delete(
            delete_type="query",
            query={"op": "=", "left": "comments.host_name", "right": "heute"},
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_delete_comments_by_params_hostname(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: id is_service",
            "Filter: host_name = heute",
        ]
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_COMMENT;1", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_COMMENT;2", match_type="ellipsis")

    with mock_livestatus:
        clients.Comment.delete(
            delete_type="params",
            host_name="heute",
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_delete_comments_by_params_service_description(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        [
            "GET comments",
            "Columns: id is_service",
            "Filter: host_name = heute",
            "Filter: service_description = service_2",
            "And: 2",
        ],
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_COMMENT;2", match_type="ellipsis")
    with mock_livestatus:
        clients.Comment.delete(
            delete_type="params",
            host_name="heute",
            service_descriptions=["service_2"],
        )
