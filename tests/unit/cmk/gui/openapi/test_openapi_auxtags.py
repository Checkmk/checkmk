#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry


def test_create_auxtag_invalid_data(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data, expect_ok=False).assert_status_code(400)

    test_data.update({"title": None})
    clients.AuxTag.create(tag_data=test_data, expect_ok=False).assert_status_code(400)

    test_data.update({"title": "aux_tag_1", "topic": ""})
    clients.AuxTag.create(tag_data=test_data, expect_ok=False).assert_status_code(400)

    test_data.update({"topic": None})
    clients.AuxTag.create(tag_data=test_data, expect_ok=False).assert_status_code(400)


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_update_auxtag_invalid_data(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)

    test_data.update({"title": ""})
    clients.AuxTag.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)

    test_data.update({"title": "aux_tag_1", "topic": None})
    clients.AuxTag.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)

    test_data.update({"topic": ""})
    clients.AuxTag.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)

    test_data.update({"topic": None})
    clients.AuxTag.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
        expect_ok=False,
    ).assert_status_code(400)


def test_get_auxtag(clients: ClientRegistry) -> None:
    resp = clients.AuxTag.get(aux_tag_id="ping")
    assert resp.json["extensions"].keys() == {"topic", "help"}
    assert {link["method"] for link in resp.json["links"]} == {
        "GET",
        "DELETE",
        "PUT",
    }


def test_get_builtin_auxtags(clients: ClientRegistry) -> None:
    assert {t["id"] for t in clients.AuxTag.get_all().json["value"]} == {
        "ip-v4",
        "ip-v6",
        "snmp",
        "tcp",
        "checkmk-agent",
        "ping",
    }


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_get_builtin_and_custom_auxtags(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)

    assert {t["id"] for t in clients.AuxTag.get_all().json["value"]} == {
        "aux_tag_id_1",
        "ip-v4",
        "ip-v6",
        "snmp",
        "tcp",
        "checkmk-agent",
        "ping",
    }


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_update_custom_aux_tag_title(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)

    test_data.update({"title": "edited_title"})
    test_data.pop("aux_tag_id")

    assert (
        clients.AuxTag.edit(
            aux_tag_id="aux_tag_id_1",
            tag_data=test_data,
        ).json["title"]
        == "edited_title"
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_update_custom_aux_tag_topic_and_help(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)
    test_data.update({"topic": "edited_topic", "help": "edited_help"})
    test_data.pop("aux_tag_id")
    resp = clients.AuxTag.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data=test_data,
    )
    assert resp.json["extensions"]["topic"] == "edited_topic"
    assert resp.json["extensions"]["help"] == "edited_help"


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_delete_custom_aux_tag(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)
    clients.AuxTag.get(aux_tag_id="aux_tag_id_1")
    clients.AuxTag.delete(aux_tag_id="aux_tag_id_1").assert_status_code(status_code=204)
    clients.AuxTag.get(aux_tag_id="aux_tag_id_1", expect_ok=False).assert_status_code(
        status_code=404
    )


def test_edit_non_existing_aux_tag(clients: ClientRegistry) -> None:
    clients.AuxTag.edit(
        aux_tag_id="aux_tag_id_1",
        tag_data={},
        expect_ok=False,
        with_etag=False,
    ).assert_status_code(404)


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_delete_tag_that_belongs_to_a_tag_group(clients: ClientRegistry) -> None:
    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)

    clients.HostTagGroup.create(
        ident="tag_group_id_1",
        title="tag_group_1",
        tags=[
            {"id": "tag_id", "title": "tag_title", "aux_tags": ["aux_tag_id_1"]},
        ],
    )

    clients.HostTagGroup.create(
        ident="tag_group_id_2",
        title="tag_group_2",
        tags=[
            {"id": "tag_id", "title": "tag_title", "aux_tags": ["aux_tag_id_1"]},
        ],
    )

    resp = clients.AuxTag.delete(
        aux_tag_id="aux_tag_id_1",
        expect_ok=False,
    )

    resp.assert_status_code(409)
    assert resp.json["title"] == "Aux tag in use"
    assert (
        resp.json["detail"]
        == 'You cannot delete this auxiliary tag. It is being used by the following tag groups: "tag_group_1, tag_group_2"'
    )


def test_update_builtin_aux_tag(clients: ClientRegistry) -> None:
    r = clients.AuxTag.edit(
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


invalid_aux_tag_ids = (
    "aux_tag_id_test\\n",
    "aux_tag_id_test\n",
    "aux_tag\n_id_test",
    "\naux_tag_id_test",
)


@pytest.mark.parametrize("aux_tag_id", invalid_aux_tag_ids)
def test_create_host_tag_with_newline_in_the_id(
    clients: ClientRegistry,
    aux_tag_id: str,
) -> None:
    resp = clients.AuxTag.create(
        tag_data={
            "aux_tag_id": aux_tag_id,
            "title": "aux_tag_1",
            "topic": "topic_1",
            "help": "HELP",
        },
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["aux_tag_id"][0]
        == f"{aux_tag_id!r} does not match pattern '^[-0-9a-zA-Z_]+\\\\Z'."
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_id_already_in_use_by_custom_tag_group(clients: ClientRegistry) -> None:
    custom_tag_group = "criticality"
    clients.HostTagGroup.create(
        ident=custom_tag_group,
        title="tag_group_1",
        tags=[
            {"id": "prod", "title": "Production"},
            {"id": "test", "title": "Testing site"},
            {"id": "beta", "title": "Beta site"},
        ],
    )

    custom_tag_group_resp = clients.AuxTag.create(
        tag_data={
            "aux_tag_id": custom_tag_group,
            "title": "aux_tag_2",
            "topic": "topic_2",
        },
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The id '{custom_tag_group}' is already in use by a tag group."
        in custom_tag_group_resp.json["fields"]["aux_tag_id"]
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_id_already_in_use_by_builtin_tag_group(clients: ClientRegistry) -> None:
    builtin_tag_group = "agent"
    builtin_tag_group_resp = clients.AuxTag.create(
        tag_data={
            "aux_tag_id": builtin_tag_group,
            "title": "aux_tag_3",
            "topic": "topic_3",
        },
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The id '{builtin_tag_group}' is already in use by a tag group."
        in builtin_tag_group_resp.json["fields"]["aux_tag_id"]
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_id_already_in_use_by_custom_aux_tag(clients: ClientRegistry) -> None:
    custom_aux_tag = "interface"

    clients.AuxTag.create(
        tag_data={
            "aux_tag_id": custom_aux_tag,
            "title": "aux_tag_1",
            "topic": "topic_1",
        },
    )

    custom_aux_tag_resp = clients.AuxTag.create(
        tag_data={
            "aux_tag_id": custom_aux_tag,
            "title": "aux_tag_1",
            "topic": "topic_1",
        },
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The aux_tag '{custom_aux_tag}' should not exist but it does."
        in custom_aux_tag_resp.json["fields"]["aux_tag_id"]
    )


def test_id_in_use_by_builtin_aux_tag(clients: ClientRegistry) -> None:
    builtin_aux_tag = "snmp"

    builtin_aux_tag_resp = clients.AuxTag.create(
        tag_data={
            "aux_tag_id": builtin_aux_tag,
            "title": "aux_tag_4",
            "topic": "topic_4",
        },
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The aux_tag '{builtin_aux_tag}' should not exist but it does."
        in builtin_aux_tag_resp.json["fields"]["aux_tag_id"]
    )
