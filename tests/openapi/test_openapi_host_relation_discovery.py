#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from http import HTTPStatus

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

_ILO: dict[str, object] = {"id": "word:ilo", "kind": "management", "words": ["ilo"]}


def _create_fleet(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/"}
            for name in ("srv-01", "srv-01-ilo", "srv-02", "gateway")
        ]
    )


def _paired_by_label(name: str) -> dict[str, object]:
    return {
        "id": f"label:{name}",
        "kind": "management",
        "paired_by": {"source": "label", "name": name},
    }


def _scan(clients: ClientRegistry, findings: list[dict[str, object]] | None = None) -> str:
    return str(clients.HostRelationDiscovery.scan(findings).json["job_id"])


def _rows(
    clients: ClientRegistry, job_id: str, query: Mapping[str, str | int] | None = None
) -> list[tuple[str, str, str]]:
    page = clients.HostRelationDiscovery.rows(job_id, query).json
    return [(row["source_host"], row["target_host"], row["outcome"]) for row in page["relations"]]


@pytest.mark.usefixtures("inline_background_jobs")
def test_a_scan_proposes_what_the_host_names_speak_for(clients: ClientRegistry) -> None:
    _create_fleet(clients)

    scan_id = _scan(clients, [_ILO])

    assert _rows(clients, scan_id) == [("srv-01-ilo", "srv-01", "link")]


@pytest.mark.usefixtures("inline_background_jobs")
def test_a_finished_scan_sums_up_every_finding(clients: ClientRegistry) -> None:
    _create_fleet(clients)

    summary = clients.HostRelationDiscovery.show(_scan(clients, [_ILO])).json["scan"]

    assert summary["hosts_scanned"] == 4
    (finding,) = summary["findings"]
    assert (finding["id"], finding["counts"]["link"]) == ("word:ilo", 1)
    assert [sample["source_host"] for sample in finding["samples"]] == ["srv-01-ilo"]


@pytest.mark.usefixtures("inline_background_jobs")
def test_a_scan_says_what_speaks_for_each_proposal(clients: ClientRegistry) -> None:
    _create_fleet(clients)

    (row,) = clients.HostRelationDiscovery.rows(_scan(clients, [_ILO])).json["relations"]

    assert (row["finding"], row["evidence"]) == (
        "word:ilo",
        'The name is "srv-01" with "ilo" added.',
    )
    assert row["reason"] == {"word": "ilo", "source": None, "name": None, "value": None}


@pytest.mark.usefixtures("inline_background_jobs")
def test_a_scan_changes_nothing(clients: ClientRegistry) -> None:
    _create_fleet(clients)

    _scan(clients, [_ILO])

    attributes = clients.HostConfig.get(host_name="srv-01").json["extensions"]["attributes"]
    assert "relations" not in attributes


@pytest.mark.usefixtures("inline_background_jobs")
def test_the_rows_of_a_scan_are_read_a_page_at_a_time(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/"}
            for index in range(5)
            for name in (f"srv-{index}", f"srv-{index}-ilo")
        ]
    )
    scan_id = _scan(clients, [_ILO])

    page = clients.HostRelationDiscovery.rows(scan_id, {"offset": 2, "limit": 2}).json

    assert page["total"] == 5
    assert [row["source_host"] for row in page["relations"]] == ["srv-2-ilo", "srv-3-ilo"]


@pytest.mark.usefixtures("inline_background_jobs")
def test_the_rows_of_a_scan_are_narrowed_down_to_a_host(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/"}
            for name in ("web-01", "web-01-ilo", "db-01", "db-01-ilo")
        ]
    )

    assert _rows(clients, _scan(clients, [_ILO]), {"search": "web"}) == [
        ("web-01-ilo", "web-01", "link")
    ]


@pytest.mark.usefixtures("inline_background_jobs")
def test_every_storable_relation_a_filter_matches_is_named_on_request(
    clients: ClientRegistry,
) -> None:
    """What "untick all of them" takes out of a run: the matches on every page, not just one."""
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/"}
            for index in range(5)
            for name in (f"web-{index}", f"web-{index}-ilo")
        ]
    )
    scan_id = _scan(clients, [_ILO])

    page = clients.HostRelationDiscovery.rows(
        scan_id, {"search": "web", "limit": 2, "all_keys": "true"}
    ).json

    assert len(page["relations"]) == 2
    assert page["keys"] == [f"web-{index}-ilo|management|web-{index}" for index in range(5)]


@pytest.mark.usefixtures("inline_background_jobs")
def test_a_scan_narrowed_to_a_folder_proposes_the_relations_with_a_host_in_it(
    clients: ClientRegistry,
) -> None:
    clients.Folder.create(folder_name="oob", title="OOB", parent="~")
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": "srv-01-ilo", "folder": "/oob"},
            {"host_name": "srv-01", "folder": "/"},
            {"host_name": "srv-02-ilo", "folder": "/"},
            {"host_name": "srv-02", "folder": "/"},
        ]
    )

    scan_id = str(
        clients.HostRelationDiscovery.scan([_ILO], scope={"folder": "/oob"}).json["job_id"]
    )

    assert _rows(clients, scan_id) == [("srv-01-ilo", "srv-01", "link")]


def test_a_scan_narrowed_to_a_folder_that_does_not_exist_is_refused(
    clients: ClientRegistry,
) -> None:
    resp = clients.HostRelationDiscovery.scan([_ILO], scope={"folder": "/nope"}, expect_ok=False)

    resp.assert_status_code(400)


def test_a_scan_narrowed_to_a_site_that_does_not_exist_is_refused(
    clients: ClientRegistry,
) -> None:
    resp = clients.HostRelationDiscovery.scan([_ILO], scope={"site": "nowhere"}, expect_ok=False)

    resp.assert_status_code(400)


def test_suggestions_narrowed_to_a_folder_that_does_not_exist_are_refused(
    clients: ClientRegistry,
) -> None:
    resp = clients.HostRelationDiscovery.suggest(scope={"folder": "/nope"}, expect_ok=False)

    resp.assert_status_code(400)


@pytest.mark.parametrize(
    "finding",
    [
        pytest.param(
            {
                "id": "x",
                "kind": "management",
                "marked_by": {"source": "label", "name": "cmdb/kind", "value": "board"},
            },
            id="a value mark without a value to pair on",
        ),
        pytest.param(
            {"id": "x", "kind": "management", "words": ["my-board"]},
            id="a word no host name could carry",
        ),
        pytest.param(
            {"id": "x", "kind": "made_up", "words": ["ilo"]},
            id="a relation that cannot be discovered",
        ),
    ],
)
def test_a_finding_that_could_not_find_anything_is_refused(
    clients: ClientRegistry, finding: dict[str, object]
) -> None:
    resp = clients.HostRelationDiscovery.scan([finding], expect_ok=False)

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_a_scan_that_looks_for_nothing_is_refused(clients: ClientRegistry) -> None:
    resp = clients.HostRelationDiscovery.scan([], expect_ok=False)

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_two_findings_under_one_id_are_refused(clients: ClientRegistry) -> None:
    resp = clients.HostRelationDiscovery.scan([_ILO, _ILO], expect_ok=False)

    assert resp.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.usefixtures("inline_background_jobs")
def test_hosts_sharing_a_value_with_no_board_among_them_are_asked_about(
    clients: ClientRegistry,
) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/", "attributes": {"labels": {"serial": "5XJ9K2"}}}
            for name in ("srv-01", "srv-02")
        ]
    )
    scan_id = _scan(clients, [_paired_by_label("serial")])

    (group,) = clients.HostRelationDiscovery.rows(scan_id, {"part": "groups"}).json["groups"]
    assert (group["members"], group["outcome"], group["relation"]) == (
        ["srv-01", "srv-02"],
        "undecided",
        "management_parent",
    )


@pytest.mark.usefixtures("inline_background_jobs")
def test_an_accepted_finding_is_stored(clients: ClientRegistry) -> None:
    _create_fleet(clients)
    scan_id = _scan(clients, [_ILO])

    run_id = clients.HostRelationDiscovery.accept(scan_id, ["word:ilo"]).json["job_id"]

    status = clients.HostRelationDiscovery.show(run_id).json
    assert status["running"] is False
    assert "1 stored" in status["summary"]
    assert status["run"]["findings"][0]["counts"]["link"] == 1


@pytest.mark.usefixtures("inline_background_jobs")
def test_a_relation_taken_out_of_a_finding_is_not_stored(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/"}
            for name in ("srv-01", "srv-01-ilo", "srv-02", "srv-02-ilo")
        ]
    )
    scan_id = _scan(clients, [_ILO])

    run_id = clients.HostRelationDiscovery.accept(
        scan_id, ["word:ilo"], excluded=["srv-02-ilo|management|srv-02"]
    ).json["job_id"]

    assert "1 stored" in clients.HostRelationDiscovery.show(run_id).json["summary"]


@pytest.mark.usefixtures("inline_background_jobs")
def test_an_answered_group_is_stored_as_ordinary_relations(clients: ClientRegistry) -> None:
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": name, "folder": "/", "attributes": {"labels": {"serial": "5XJ9K2"}}}
            for name in ("srv-01", "srv-02", "srv-03")
        ]
    )
    scan_id = _scan(clients, [_paired_by_label("serial")])
    (group,) = clients.HostRelationDiscovery.rows(scan_id, {"part": "groups"}).json["groups"]

    run_id = clients.HostRelationDiscovery.accept(
        scan_id, ["label:serial"], answers={group["key"]: "srv-01"}
    ).json["job_id"]

    assert "2 stored" in clients.HostRelationDiscovery.show(run_id).json["summary"]


@pytest.mark.usefixtures("inline_background_jobs")
def test_an_answer_the_scan_did_not_ask_for_is_refused(clients: ClientRegistry) -> None:
    _create_fleet(clients)
    scan_id = _scan(clients, [_ILO])

    resp = clients.HostRelationDiscovery.accept(
        scan_id, ["word:ilo"], answers={"management|a,b": "a"}, expect_ok=False
    )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_a_scan_that_does_not_exist_cannot_be_stored_from(clients: ClientRegistry) -> None:
    resp = clients.HostRelationDiscovery.accept("relation_scan-gone", ["word:ilo"], expect_ok=False)

    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_a_job_of_another_feature_is_not_shown_here(clients: ClientRegistry) -> None:
    resp = clients.HostRelationDiscovery.show("parent_scan", expect_ok=False)

    assert resp.status_code == HTTPStatus.NOT_FOUND


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

    assert resp.status_code == HTTPStatus.BAD_REQUEST


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
        {"value": "S-0", "hosts": ["w-0b", "w-0s"], "size": 2},
        {"value": "S-1", "hosts": ["w-1b", "w-1s"], "size": 2},
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

    resp.assert_status_code(HTTPStatus.BAD_REQUEST)


@pytest.mark.usefixtures("inline_background_jobs")
def test_words_and_a_shared_value_of_one_relation_are_read_together(
    clients: ClientRegistry,
) -> None:
    """Two findings of the same relation: part of the fleet is named, part is in the CMDB."""
    clients.HostConfig.bulk_create(
        entries=[
            {"host_name": "srv-01", "folder": "/"},
            {"host_name": "srv-01-ilo", "folder": "/"},
            {"host_name": "w-4711", "folder": "/", "attributes": {"labels": {"cmdb/sn": "S-1"}}},
            {
                "host_name": "w-4712",
                "folder": "/",
                "attributes": {"labels": {"cmdb/sn": "S-1", "cmdb/kind": "board"}},
            },
        ]
    )
    scan_id = _scan(
        clients,
        [
            _ILO,
            {
                "id": "label:cmdb/sn",
                "kind": "management",
                "marked_by": {"source": "label", "name": "cmdb/kind", "value": "board"},
                "paired_by": {"source": "label", "name": "cmdb/sn"},
            },
        ],
    )

    assert sorted(_rows(clients, scan_id)) == [
        ("srv-01-ilo", "srv-01", "link"),
        ("w-4712", "w-4711", "link"),
    ]


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
