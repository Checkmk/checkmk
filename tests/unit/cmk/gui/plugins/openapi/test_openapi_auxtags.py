#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from tests.testlib.rest_api_client import AuxTagTestClient, HostTagGroupTestClient


def test_create_auxtag_invalid_data(auxtag_client: AuxTagTestClient) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data, expect_ok=False).assert_status_code(400)

    test_data.update({"title": None})
    auxtag_client.create(tag_data=test_data, expect_ok=False).assert_status_code(400)

    test_data.update({"title": "aux_tag_1", "topic": ""})
    auxtag_client.create(tag_data=test_data, expect_ok=False).assert_status_code(400)

    test_data.update({"topic": None})
    auxtag_client.create(tag_data=test_data, expect_ok=False).assert_status_code(400)


def test_update_auxtag_invalid_data(auxtag_client: AuxTagTestClient) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data)

    test_data.update({"title": ""})
    auxtag_client.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)

    test_data.update({"title": "aux_tag_1", "topic": None})
    auxtag_client.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)

    test_data.update({"topic": ""})
    auxtag_client.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)

    test_data.update({"topic": None})
    auxtag_client.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)


def test_get_auxtag(auxtag_client: AuxTagTestClient) -> None:
    resp = auxtag_client.get(aux_tag_id="ping")
    assert resp.json["extensions"].keys() == {"topic", "help"}
    assert {link["method"] for link in resp.json["links"]} == {
        "GET",
        "DELETE",
        "PUT",
    }


def test_get_builtin_auxtags(auxtag_client: AuxTagTestClient) -> None:
    assert {t["id"] for t in auxtag_client.get_all().json["value"]} == {
        "ip-v4",
        "ip-v6",
        "snmp",
        "tcp",
        "checkmk-agent",
        "ping",
    }


def test_get_builtin_and_custom_auxtags(auxtag_client: AuxTagTestClient) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data)

    assert {t["id"] for t in auxtag_client.get_all().json["value"]} == {
        "aux_tag_id_1",
        "ip-v4",
        "ip-v6",
        "snmp",
        "tcp",
        "checkmk-agent",
        "ping",
    }


def test_update_custom_aux_tag_title(auxtag_client: AuxTagTestClient) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data)

    test_data.update({"title": "edited_title"})
    test_data.pop("aux_tag_id")

    assert (
        auxtag_client.edit(
            aux_tag_id="aux_tag_id_1",
            tag_data=test_data,
        ).json["title"]
        == "edited_title"
    )


def test_update_custom_aux_tag_topic_and_help(auxtag_client: AuxTagTestClient) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data)
    test_data.update({"topic": "edited_topic", "help": "edited_help"})
    test_data.pop("aux_tag_id")
    resp = auxtag_client.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
    )
    assert resp.json["extensions"]["topic"] == "edited_topic"
    assert resp.json["extensions"]["help"] == "edited_help"


def test_delete_custom_aux_tag(auxtag_client: AuxTagTestClient) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data)
    auxtag_client.get(aux_tag_id="aux_tag_id_1")
    auxtag_client.delete(aux_tag_id="aux_tag_id_1").assert_status_code(status_code=204)
    auxtag_client.get(aux_tag_id="aux_tag_id_1", expect_ok=False).assert_status_code(
        status_code=404
    )


def test_edit_non_existing_aux_tag(auxtag_client: AuxTagTestClient) -> None:
    auxtag_client.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data={},
        expect_ok=False,
        with_etag=False,
    ).assert_status_code(404)


def test_delete_tag_that_belongs_to_a_tag_group(
    auxtag_client: AuxTagTestClient, host_tag_group_client: HostTagGroupTestClient
) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    auxtag_client.create(tag_data=test_data)

    host_tag_group_client.create(
        ident="tag_group_id_1",
        title="tag_group_1",
        tags=[
            {"ident": "tag_id", "title": "tag_title", "aux_tags": ["aux_tag_id_1"]},
        ],
    )

    host_tag_group_client.create(
        ident="tag_group_id_2",
        title="tag_group_2",
        tags=[
            {"ident": "tag_id", "title": "tag_title", "aux_tags": ["aux_tag_id_1"]},
        ],
    )

    resp = auxtag_client.delete(
        aux_tag_id="aux_tag_id_1",
        expect_ok=False,
    )

    resp.assert_status_code(409)
    assert resp.json["title"] == "Aux tag in use"
    assert (
        resp.json["detail"]
        == 'You cannot delete this auxiliary tag. It is being used by the following tag groups: "tag_group_1, tag_group_2"'
    )


def test_update_builtin_aux_tag(auxtag_client: AuxTagTestClient) -> None:
    r = auxtag_client.edit(
        aux_tag_id="ip-v4",
        tag_data={},
        expect_ok=False,
        with_etag=False,
    )
    r.assert_status_code(404)
    assert r.json["title"] == "Not Found"
    assert (
        r.json["fields"]["aux_tag_id"][0]
        == "The aux_tag 'ip-v4' should be an existing custom aux tag but it's not."
    )
