#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.testlib.rest_api_client import AuxTagTestClient


def test_create_auxtag_invalid_data(auxtag_client: AuxTagTestClient) -> None:
    auxtag_client.create(
        expect_ok=False,
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="",
            topic="topic_1",
        ),
    ).assert_status_code(400)

    auxtag_client.create(
        expect_ok=False,
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title=None,
            topic="topic_1",
        ),
    ).assert_status_code(400)

    auxtag_client.create(
        expect_ok=False,
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic="",
        ),
    ).assert_status_code(400)

    auxtag_client.create(
        expect_ok=False,
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic=None,
        ),
    ).assert_status_code(400)


def test_update_auxtag_invalid_data(auxtag_client: AuxTagTestClient) -> None:
    auxtag_client.create(
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic="topic_1",
        )
    )
    auxtag_client.edit(
        expect_ok=False,
        aux_tag_id="aux_tag_id_1",
        tag_data=auxtag_client.edit_model(
            title="",
            topic="topic_1",
        ),
    ).assert_status_code(400)

    auxtag_client.edit(
        expect_ok=False,
        aux_tag_id="aux_tag_id_1",
        tag_data=auxtag_client.edit_model(
            title=None,
            topic="topic_1",
        ),
    ).assert_status_code(400)

    auxtag_client.edit(
        expect_ok=False,
        aux_tag_id="aux_tag_id_1",
        tag_data=auxtag_client.edit_model(
            title="aux_tag_1",
            topic="",
        ),
    ).assert_status_code(400)

    auxtag_client.edit(
        expect_ok=False,
        aux_tag_id="aux_tag_id_1",
        tag_data=auxtag_client.edit_model(
            title="aux_tag_1",
            topic=None,
        ),
    ).assert_status_code(400)


def test_get_auxtag(auxtag_client: AuxTagTestClient) -> None:
    resp = auxtag_client.get(aux_tag_id="ping")
    assert resp.json["extensions"].keys() == {"topic"}
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
    auxtag_client.create(
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic="topic_1",
        )
    )

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
    auxtag_client.create(
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic="topic_1",
        )
    )
    assert (
        auxtag_client.edit(
            aux_tag_id="aux_tag_id_1",
            tag_data=auxtag_client.edit_model(
                title="edited_title",
                topic="topic_1",
            ),
        ).json["title"]
        == "edited_title"
    )


def test_update_custom_aux_tag_topic(auxtag_client: AuxTagTestClient) -> None:
    auxtag_client.create(
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic="topic_1",
        )
    )
    assert (
        auxtag_client.edit(
            aux_tag_id="aux_tag_id_1",
            tag_data=auxtag_client.edit_model(
                title="edited_title",
                topic="edited_topic",
            ),
        ).json["extensions"]["topic"]
        == "edited_topic"
    )


def test_delete_custom_aux_tag(auxtag_client: AuxTagTestClient) -> None:
    auxtag_client.create(
        tag_data=auxtag_client.create_model(
            aux_tag_id="aux_tag_id_1",
            title="aux_tag_1",
            topic="topic_1",
        )
    )

    auxtag_client.get(aux_tag_id="aux_tag_id_1")
    auxtag_client.delete(aux_tag_id="aux_tag_id_1").assert_status_code(status_code=204)
    auxtag_client.get(aux_tag_id="aux_tag_id_1", expect_ok=False).assert_status_code(
        status_code=404
    )
