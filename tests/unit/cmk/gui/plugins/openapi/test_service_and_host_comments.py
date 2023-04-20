#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import random
import time
from collections.abc import Callable
from functools import partial
from typing import Any

import pytest
from faker import Faker

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

DOMAIN_TYPE = "comment"


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


@pytest.fixture(name="object_base_url")
def object_url(base: str) -> str:
    return f"{base}/objects/{DOMAIN_TYPE}/"


@pytest.fixture(name="collection_base_url")
def collection_url(base: str) -> str:
    return f"{base}/domain-types/{DOMAIN_TYPE}/collections/"


# TODO Move the 'partial' fixtures to conftest and give general name


@pytest.fixture(name="get_comment")
def partial_get(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="get_comments")
def partial_list(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.get,
        status=200,
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="bulk_delete")
def partial_bulk_delete(aut_user_auth_wsgi_app: WebTestAppForCMK, base: str) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        url=f"{base}/domain-types/{DOMAIN_TYPE}/actions/delete/invoke",
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


@pytest.fixture(name="post_comment")
def partial_post(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Callable:
    return partial(
        aut_user_auth_wsgi_app.post,
        status=204,
        content_type="application/json",
        headers={"Accept": "application/json"},
    )


def test_get_all_comments(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service"
    )
    with mock_livestatus:
        resp = get_comments(collection_base_url + "all")
        assert resp.json["domainType"] == DOMAIN_TYPE


def test_get_host_comments(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 0"
    )
    with mock_livestatus:
        get_comments(url=collection_base_url + "host")


def test_get_service_comments(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 1"
    )
    with mock_livestatus:
        get_comments(url=collection_base_url + "service")


def test_get_comments_that_dont_exist(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = non_existing_host\nFilter: service_description = non_existing_service\nAnd: 2"
    )
    with mock_livestatus:
        resp = get_comments(
            collection_base_url
            + "all?host_name=non_existing_host&service_description=non_existing_service"
        )
    assert resp.json["domainType"] == DOMAIN_TYPE
    assert resp.json["extensions"] == {}


def test_comment_params_execption(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    with mock_livestatus:
        resp = get_comments(
            url=collection_base_url + "host?host_name=heute&service_description=service_1",
            status=400,
        )
    assert resp.json["title"] == "Invalid parameter combination"
    assert (
        resp.json["detail"]
        == "You set collection_name to host but the provided filtering parameters will return only service comments."
    )


def test_get_non_existing_comment(
    mock_livestatus: MockLiveStatusConnection, get_comment: Callable, object_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: id = 100"
    )
    with mock_livestatus:
        get_comment(url=object_base_url + "100", status=404)


def test_get_comment_invalid_id(get_comment: Callable, object_base_url: str) -> None:
    resp = get_comment(url=object_base_url + "invalid_id", status=404)
    assert resp.json["title"] == "Not Found"
    assert resp.json["detail"] == "These fields have problems: comment_id"


def test_get_host_comment_by_id(
    mock_livestatus: MockLiveStatusConnection, get_comment: Callable, object_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: id = 1"
    )

    with mock_livestatus:
        resp = get_comment(url=object_base_url + "1")
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
        }


def test_get_service_comment_by_id(
    mock_livestatus: MockLiveStatusConnection, get_comment: Callable, object_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: id = 2"
    )
    with mock_livestatus:
        resp = get_comment(url=object_base_url + "2")
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
        }


def test_get_all_host_comments(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 0"
    )
    with mock_livestatus:
        resp = get_comments(url=collection_base_url + "host")
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert set(resp.json["value"][0]["extensions"].keys()) == {
            "host_name",
            "id",
            "author",
            "comment",
            "persistent",
            "entry_time",
            "is_service",
        }


def test_get_host_comments_by_query(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = heute"
    )
    with mock_livestatus:
        resp = get_comments(
            url=collection_base_url
            + 'all?query={"op": "=", "left": "comments.host_name", "right": "heute"}'
        )
        assert resp.json["domainType"] == DOMAIN_TYPE
        assert resp.json["value"][0]["extensions"]["host_name"] == "heute"


def test_get_all_service_comments(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 1"
    )
    with mock_livestatus:
        resp = get_comments(url=collection_base_url + "service")
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
        }


def test_get_service_comments_by_query(
    mock_livestatus: MockLiveStatusConnection, get_comments: Callable, collection_base_url: str
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: is_service = 1"
    )
    with mock_livestatus:
        resp = get_comments(
            url=collection_base_url
            + 'all?query={"op": "=", "left": "comments.is_service", "right": "1"}'
        )
        assert resp.json["domainType"] == DOMAIN_TYPE


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_post_host_comment(
    mock_livestatus: MockLiveStatusConnection, post_comment: Callable, collection_base_url: str
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
        post_comment(url=collection_base_url + "host", params=json.dumps(post_params))


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_post_service_comment(
    mock_livestatus: MockLiveStatusConnection,
    collection_base_url: str,
    post_comment: Callable,
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
        post_comment(url=collection_base_url + "service", params=json.dumps(post_params))


def test_post_host_comment_with_query(
    mock_livestatus: MockLiveStatusConnection,
    collection_base_url: str,
    post_comment: Callable,
) -> None:
    post_params = {
        "comment_type": "host_by_query",
        "comment": "This is a test comment",
        "query": {"op": "=", "left": "hosts.name", "right": "heute"},
    }
    mock_livestatus.expect_query("GET hosts\nColumns: name\nFilter: name = heute")
    mock_livestatus.expect_query(
        f"COMMAND [...] ADD_HOST_COMMENT;heute;0;test123-...;{post_params['comment']}",
        match_type="ellipsis",
    )
    with mock_livestatus:
        post_comment(url=collection_base_url + "host", params=json.dumps(post_params))


def test_post_service_comment_with_query(
    mock_livestatus: MockLiveStatusConnection,
    collection_base_url: str,
    post_comment: Callable,
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    post_params = {
        "comment_type": "service_by_query",
        "comment": "This is a test comment",
        "persistent": True,
        "query": {
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
    }
    mock_livestatus.expect_query(
        "GET services\nColumns: description host_name\nFilter: description = service1\nFilter: host_name = heute\nAnd: 2"
    )
    mock_livestatus.expect_query(
        f"COMMAND [...] ADD_SVC_COMMENT;heute;service1;1;test123-...;{post_params['comment']}",
        match_type="ellipsis",
    )
    with mock_livestatus:
        post_comment(url=collection_base_url + "service", params=json.dumps(post_params))


def test_post_service_comment_invalid_query(
    post_comment: Callable, collection_base_url: str
) -> None:
    post_params = {
        "comment_type": "service_by_query",
        "comment": "This is a test comment",
        "query": "something that is not a query",
    }
    resp = post_comment(
        url=collection_base_url + "service", status=400, params=json.dumps(post_params)
    )
    assert resp.json["detail"] == "These fields have problems: query"


def test_post_host_comment_invalid_query(post_comment: Callable, collection_base_url: str) -> None:
    post_params = {
        "comment_type": "host_by_query",
        "comment": "This is a test comment",
        "query": "something that is not a query",
    }
    resp = post_comment(
        url=collection_base_url + "host", status=400, params=json.dumps(post_params)
    )
    assert resp.json["detail"] == "These fields have problems: query"


def test_post_service_comment_invalid_comment_type(
    collection_base_url: str, post_comment: Callable
) -> None:
    post_params = {"comment_type": "this should not work"}
    resp = post_comment(
        url=collection_base_url + "service", status=400, params=json.dumps(post_params)
    )
    assert resp.json["detail"] == "These fields have problems: comment_type"
    assert (
        resp.json["fields"]["comment_type"][0]
        == f"Unsupported value: {post_params['comment_type']}"
    )


def test_post_host_comment_invalid_comment_type(
    post_comment: Callable, collection_base_url: str
) -> None:
    post_params = {"comment_type": "this should not work"}
    resp = post_comment(
        url=collection_base_url + "host", status=400, params=json.dumps(post_params)
    )
    assert resp.json["detail"] == "These fields have problems: comment_type"
    assert (
        resp.json["fields"]["comment_type"][0]
        == f"Unsupported value: {post_params['comment_type']}"
    )


def test_delete_comment_by_id(
    mock_livestatus: MockLiveStatusConnection, bulk_delete: Callable
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: id = 1"
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_COMMENT;1", match_type="ellipsis")
    with mock_livestatus:
        bulk_delete(
            params=json.dumps({"delete_type": "by_id", "comment_id": 1}),
        )


def test_delete_invalid_comment_ids(bulk_delete: Callable) -> None:
    for bad_int in [True, False, "abc"]:
        resp = bulk_delete(
            params=json.dumps({"delete_type": "by_id", "comment_id": bad_int}),
            status=400,
        )
        assert resp.json["title"] == "Bad Request"
        assert resp.json["detail"] == "These fields have problems: comment_id"
        assert resp.json["fields"]["comment_id"][0] == "Not a valid integer."


def test_delete_comments_by_query(
    mock_livestatus: MockLiveStatusConnection, bulk_delete: Callable
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = heute"
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_COMMENT;1", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_COMMENT;2", match_type="ellipsis")

    with mock_livestatus:
        bulk_delete(
            params=json.dumps(
                {
                    "delete_type": "query",
                    "query": '{"op": "=", "left": "comments.host_name", "right": "heute"}',
                }
            )
        )


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_delete_comments_by_params_hostname(
    mock_livestatus: MockLiveStatusConnection, bulk_delete: Callable
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = heute"
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_HOST_COMMENT;1", match_type="ellipsis")
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_COMMENT;2", match_type="ellipsis")

    with mock_livestatus:
        bulk_delete(params=json.dumps({"delete_type": "params", "host_name": "heute"}))


@pytest.mark.usefixtures("suppress_remote_automation_calls", "with_host")
def test_delete_comments_by_params_service_description(
    mock_livestatus: MockLiveStatusConnection, bulk_delete: Callable
) -> None:
    add_service_and_host_comments_to_live_status_table(mock_livestatus)
    mock_livestatus.expect_query(
        "GET comments\nColumns: host_name id author comment persistent service_description entry_time is_service\nFilter: host_name = heute\nFilter: service_description = service_2\nAnd: 2"
    )
    mock_livestatus.expect_query("COMMAND [...] DEL_SVC_COMMENT;2", match_type="ellipsis")
    with mock_livestatus:
        bulk_delete(
            params=json.dumps(
                {
                    "delete_type": "params",
                    "host_name": "heute",
                    "service_descriptions": ["service_2"],
                }
            )
        )
