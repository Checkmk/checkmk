#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.testlib.unit.rest_api_client import ClientRegistry

_ILO: dict[str, object] = {"id": "word:ilo", "kind": "management", "words": ["ilo"]}


def test_the_words_a_fleet_is_named_by_are_suggested_before_anything_is_asked(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/"}
            for name in ("srv-01", "srv-01-ilo", "srv-02", "srv-02-oob", "gateway")
        ]
    )
    resp = clients.HostRelationDiscovery.suggest()

    assert resp.json["hosts_scanned"] == 5
    assert [(word["word"], word["pairs"], word["kind"]) for word in resp.json["words"]] == [
        ("ilo", 1, "management"),
        ("oob", 1, None),
    ]
    assert resp.json["words"][0]["examples"] == [{"named": "srv-01-ilo", "base": "srv-01"}]


def test_a_word_the_user_typed_is_reported_even_if_no_host_carries_it(
    clients: ClientRegistry,
) -> None:
    resp = clients.HostRelationDiscovery.suggest(words=["oob"])

    assert resp.json["words"] == [{"word": "oob", "pairs": 0, "examples": [], "kind": None}]


def test_a_typed_word_no_host_name_could_carry_is_refused(clients: ClientRegistry) -> None:
    resp = clients.HostRelationDiscovery.suggest(words=["my-board"], expect_ok=False)

    assert resp.status_code == 400


def test_a_label_that_pairs_hosts_is_suggested_with_what_tells_them_apart(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {
                "host_name": f"w-{machine}{kind[0]}",
                "folder": "/",
                "attributes": {"labels": {"cmdb/sn": f"S-{machine}", "cmdb/kind": kind}},
            }
            for machine in range(3)
            for kind in ("board", "server")
        ]
    )
    resp = clients.HostRelationDiscovery.suggest()

    (value,) = resp.json["values"]
    assert (value["source"], value["name"], value["groups"]) == ("label", "cmdb/sn", 3)
    assert value["examples"] == [
        {"value": "S-0", "hosts": ["w-0b", "w-0s"]},
        {"value": "S-1", "hosts": ["w-1b", "w-1s"]},
    ]
    assert (value["told_apart"]["by"], value["told_apart"]["name"]) == ("value", "cmdb/kind")
    assert [counted["value"] for counted in value["told_apart"]["values"]] == ["board", "server"]


def test_looking_in_the_names_alone_leaves_the_labels_unread(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/", "attributes": {"labels": {"cmdb/sn": "S-1"}}}
            for name in ("srv-01", "srv-01-ilo")
        ]
    )

    # Outside a mocked monitoring: asking the core for its labels would fail the request.
    resp = clients.HostRelationDiscovery.suggest(look_in=["names"])

    assert [word["word"] for word in resp.json["words"]] == ["ilo"]
    assert resp.json["values"] == []


def test_a_suggestion_has_to_look_somewhere(clients: ClientRegistry) -> None:
    resp = clients.HostRelationDiscovery.suggest(look_in=[], expect_ok=False)

    resp.assert_status_code(400)


def test_a_value_the_user_added_is_reported_with_what_it_finds(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/", "attributes": {"labels": {"location": "ber"}}}
            for name in ("a", "b", "c")
        ]
    )
    resp = clients.HostRelationDiscovery.suggest(values=[{"source": "label", "name": "location"}])

    (value,) = resp.json["values"]
    assert (value["name"], value["groups"], value["largest_group"]) == ("location", 1, 3)
