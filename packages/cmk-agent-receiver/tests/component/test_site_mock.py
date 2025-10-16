#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

import httpx
import pytest

from cmk.testlib.agent_receiver.site_mock import (
    GetResponse,
    ListResponse,
    OP,
    PostResponse,
    SiteMock,
    User,
)


@pytest.fixture
def client(site: SiteMock, user: User) -> httpx.Client:
    return httpx.Client(
        base_url=site.base_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": user.bearer,
        },
    )


def test_can_only_setup_one_scenario(site: SiteMock) -> None:
    relays = ["a", "b"]
    site.set_scenario(relays=relays)
    with pytest.raises(RuntimeError):
        site.set_scenario(relays=relays)


@pytest.mark.parametrize(
    "relays",
    [
        pytest.param(["relay_1"], id="single relay"),
        pytest.param(["relay_1", "relay_2", "relay_3"], id="multiple relay"),
    ],
)
def test_scenario_initial_conditions_match(
    site: SiteMock, relays: list[str], client: httpx.Client
) -> None:
    site.set_scenario(relays=relays)

    # confirm we get correct infos for each single relay
    for rid in relays:
        resp = client.get(f"/objects/relay/{rid}")
        assert resp.status_code == HTTPStatus.OK, resp.url
        parsed = GetResponse.model_validate(resp.json())
        assert parsed.id == rid

    # collection works as well
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK, resp.url
    list_parsed = ListResponse.model_validate(resp.json())
    reply_relay_ids = {r.id for r in list_parsed.value}
    assert reply_relay_ids == set(relays)


def test_scenario_can_add_relay(site: SiteMock, client: httpx.Client) -> None:
    relays = ["a", "b"]
    new_relay = "relay2"
    site.set_scenario(relays=relays, changes=[(new_relay, OP.ADD)])

    # we add a relay
    resp = client.post(
        "/domain-types/relay/collections/all",
        json={
            "alias": new_relay,
            "siteid": site.site_name,
            "num_fetchers": 17,
            "log_level": "INFO",
        },
    )
    assert resp.status_code == HTTPStatus.OK, resp.url
    parsed = PostResponse.model_validate(resp.json())
    assert parsed.id == new_relay

    # we can obtain it
    resp = client.get(f"/objects/relay/{new_relay}")
    assert resp.status_code == HTTPStatus.OK, resp.url

    # we see it in the whole collection
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK, resp.url
    list_parsed = ListResponse.model_validate(resp.json())
    assert new_relay in {r.id for r in list_parsed.value}


def test_scenario_can_delete_relay(site: SiteMock, client: httpx.Client) -> None:
    relays = ["a", "b"]
    to_delete_relay = "b"
    site.set_scenario(relays=relays, changes=[(to_delete_relay, OP.DEL)])

    # we delete a relay
    resp = client.delete(f"/objects/relay/{to_delete_relay}")
    assert resp.status_code == HTTPStatus.NO_CONTENT, resp.text

    # we cannot obtain it
    resp = client.get(f"/objects/relay/{to_delete_relay}")
    assert resp.status_code == HTTPStatus.NOT_FOUND, resp.url

    # we see it in the whole collection
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK, resp.url
    list_parsed = ListResponse.model_validate(resp.json())
    assert to_delete_relay not in {r.id for r in list_parsed.value}


def test_scenario_start_empty_add_relay(site: SiteMock, client: httpx.Client) -> None:
    new_relay = "relay_first"
    site.set_scenario(relays=[], changes=[(new_relay, OP.ADD)])

    # verify initial state - should be empty
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    assert len(list_parsed.value) == 0

    # add the first relay
    resp = client.post(
        "/domain-types/relay/collections/all",
        json={
            "alias": new_relay,
            "siteid": site.site_name,
            "num_fetchers": 17,
            "log_level": "INFO",
        },
    )
    assert resp.status_code == HTTPStatus.OK
    parsed = PostResponse.model_validate(resp.json())
    assert parsed.id == new_relay

    # verify we can get it
    resp = client.get(f"/objects/relay/{new_relay}")
    assert resp.status_code == HTTPStatus.OK
    get_parsed = GetResponse.model_validate(resp.json())
    assert get_parsed.id == new_relay

    # verify it's in the collection
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    assert len(list_parsed.value) == 1
    assert list_parsed.value[0].id == new_relay


def test_scenario_multiple_changes(site: SiteMock, client: httpx.Client) -> None:
    initial_relays = ["relay_a", "relay_b"]
    changes = [
        ("relay_new1", OP.ADD),
        ("relay_a", OP.DEL),
        ("relay_new2", OP.ADD),
        ("relay_b", OP.DEL),
        ("relay_final", OP.ADD),
    ]

    site.set_scenario(relays=initial_relays, changes=changes)

    # verify initial state - should have relay_a and relay_b
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    current_relay_ids = {r.id for r in list_parsed.value}
    assert current_relay_ids == {"relay_a", "relay_b"}

    # step 1: add relay_new1
    resp = client.post(
        "/domain-types/relay/collections/all",
        json={
            "alias": "relay_new1",
            "siteid": site.site_name,
            "num_fetchers": 17,
            "log_level": "INFO",
        },
    )
    assert resp.status_code == HTTPStatus.OK
    parsed = PostResponse.model_validate(resp.json())
    assert parsed.id == "relay_new1"

    # verify state after first add
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    current_relay_ids = {r.id for r in list_parsed.value}
    assert current_relay_ids == {"relay_a", "relay_b", "relay_new1"}

    # step 2: delete relay_a
    resp = client.delete("/objects/relay/relay_a")
    assert resp.status_code == HTTPStatus.NO_CONTENT

    # verify relay_a is gone
    resp = client.get("/objects/relay/relay_a")
    assert resp.status_code == HTTPStatus.NOT_FOUND

    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    current_relay_ids = {r.id for r in list_parsed.value}
    assert current_relay_ids == {"relay_b", "relay_new1"}

    # step 3: add relay_new2
    resp = client.post(
        "/domain-types/relay/collections/all",
        json={
            "alias": "relay_new2",
            "siteid": site.site_name,
            "num_fetchers": 17,
            "log_level": "INFO",
        },
    )
    assert resp.status_code == HTTPStatus.OK
    parsed = PostResponse.model_validate(resp.json())
    assert parsed.id == "relay_new2"

    # verify state after second add
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    current_relay_ids = {r.id for r in list_parsed.value}
    assert current_relay_ids == {"relay_b", "relay_new1", "relay_new2"}

    # step 4: delete relay_b
    resp = client.delete("/objects/relay/relay_b")
    assert resp.status_code == HTTPStatus.NO_CONTENT

    # verify relay_b is gone
    resp = client.get("/objects/relay/relay_b")
    assert resp.status_code == HTTPStatus.NOT_FOUND

    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    current_relay_ids = {r.id for r in list_parsed.value}
    assert current_relay_ids == {"relay_new1", "relay_new2"}

    # step 5: add relay_final
    resp = client.post(
        "/domain-types/relay/collections/all",
        json={
            "alias": "relay_final",
            "siteid": site.site_name,
            "num_fetchers": 17,
            "log_level": "INFO",
        },
    )
    assert resp.status_code == HTTPStatus.OK
    parsed = PostResponse.model_validate(resp.json())
    assert parsed.id == "relay_final"

    # verify final state
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())
    current_relay_ids = {r.id for r in list_parsed.value}
    assert current_relay_ids == {"relay_new1", "relay_new2", "relay_final"}

    # verify we can get each relay individually
    for relay_id in ["relay_new1", "relay_new2", "relay_final"]:
        resp = client.get(f"/objects/relay/{relay_id}")
        assert resp.status_code == HTTPStatus.OK
        get_parsed = GetResponse.model_validate(resp.json())
        assert get_parsed.id == relay_id


def test_sitename_alias_return_bodies(site: SiteMock, client: httpx.Client) -> None:
    test_relays = ["relay_with_alias", "another_relay"]
    site.set_scenario(relays=test_relays)

    # test single relay endpoint returns correct sitename and alias
    for relay_id in test_relays:
        resp = client.get(f"/objects/relay/{relay_id}")
        assert resp.status_code == HTTPStatus.OK
        get_parsed = GetResponse.model_validate(resp.json())
        assert get_parsed.id == relay_id
        assert get_parsed.extensions.alias == relay_id
        assert get_parsed.extensions.siteid == site.site_name

    # test collection endpoint returns correct sitename and alias for all relays
    resp = client.get("/domain-types/relay/collections/all")
    assert resp.status_code == HTTPStatus.OK
    list_parsed = ListResponse.model_validate(resp.json())

    for relay_response in list_parsed.value:
        assert relay_response.id in test_relays
        assert relay_response.extensions.alias == relay_response.id
        assert relay_response.extensions.siteid == site.site_name
