#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.testlib.rest_api_client import AuxTagJSON, RestApiClient


def get_test_data() -> list[AuxTagJSON]:
    return [
        AuxTagJSON(
            **{
                "aux_tag_id": f"aux_tag_id_{i}",
                "title": f"aux_tag_{i}",
                "topic": f"topic_{i}",
            }
        )
        for i in range(3)
    ]


def test_get_auxtag(api_client: RestApiClient) -> None:
    resp = api_client.get_aux_tag(tag_id="ping")
    assert resp.json["extensions"].keys() == {"topic"}
    assert {link["method"] for link in resp.json["links"]} == {
        "GET",
        "DELETE",
        "PUT",
    }


def test_get_builtin_auxtags(api_client: RestApiClient) -> None:
    assert {t["id"] for t in api_client.get_aux_tags().json["value"]} == {
        "ip-v4",
        "ip-v6",
        "snmp",
        "tcp",
        "checkmk-agent",
        "ping",
    }


def test_get_builtin_and_custom_auxtags(api_client: RestApiClient) -> None:
    for tag_data in get_test_data():
        api_client.create_aux_tag(tag_data=tag_data)

    assert {t["id"] for t in api_client.get_aux_tags().json["value"]} == {
        "aux_tag_id_0",
        "aux_tag_id_1",
        "aux_tag_id_2",
        "ip-v4",
        "ip-v6",
        "snmp",
        "tcp",
        "checkmk-agent",
        "ping",
    }


def test_update_custom_aux_tag_title(api_client: RestApiClient) -> None:
    aux_tag = get_test_data()[0]
    api_client.create_aux_tag(tag_data=aux_tag)
    aux_tag.title = "edited_title"
    assert api_client.edit_aux_tag(tag_data=aux_tag).json["title"] == "edited_title"


def test_update_custom_aux_tag_topic(api_client: RestApiClient) -> None:
    aux_tag = get_test_data()[0]
    api_client.create_aux_tag(tag_data=aux_tag)
    aux_tag.topic = "edited_topic"
    assert api_client.edit_aux_tag(tag_data=aux_tag).json["extensions"]["topic"] == "edited_topic"


def test_delete_custom_aux_tag(api_client: RestApiClient) -> None:
    aux_tag = get_test_data()[0]
    api_client.create_aux_tag(tag_data=aux_tag)
    api_client.get_aux_tag(tag_id=aux_tag.aux_tag_id)
    api_client.delete_aux_tag(tag_id=aux_tag.aux_tag_id).assert_status_code(status_code=204)
    api_client.get_aux_tag(tag_id=aux_tag.aux_tag_id, expect_ok=False).assert_status_code(
        status_code=404
    )
