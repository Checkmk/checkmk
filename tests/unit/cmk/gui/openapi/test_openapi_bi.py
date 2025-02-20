#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access


import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from tests.unit.cmk.web_test_app import SetConfig

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.watolib import activate_changes


def test_get_bi_packs(clients: ClientRegistry) -> None:
    packs = clients.BiPack.get_all().json
    assert packs["domainType"] == "bi_pack"
    assert len(packs["value"]) == 1
    assert packs["value"][0]["title"] == "Default Pack"


def test_get_bi_rule_non_existing_id(clients: ClientRegistry) -> None:
    clients.BiRule.get(
        rule_id="abc",
        expect_ok=False,
    ).assert_status_code(404)


def test_get_bi_aggregation_non_existing_id(
    clients: ClientRegistry,
) -> None:
    clients.BiAggregation.get(
        aggregation_id="abc",
        expect_ok=False,
    ).assert_status_code(404)


def test_get_bi_pack(clients: ClientRegistry) -> None:
    pack_id = "default"
    pack = clients.BiPack.get(pack_id=pack_id).json
    assert pack["id"] == pack_id
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1


def test_get_bi_aggregation(clients: ClientRegistry) -> None:
    aggr_id = "default_aggregation"
    aggregation = clients.BiAggregation.get(aggregation_id=aggr_id).json
    for required_key in [
        "aggregation_visualization",
        "computation_options",
        "groups",
        "id",
        "node",
        "pack_id",
    ]:
        assert required_key in aggregation
    assert aggregation["id"] == aggr_id


def test_get_bi_rule(clients: ClientRegistry) -> None:
    rule_id = "applications"
    rule = clients.BiRule.get(rule_id=rule_id).json
    for required_key in [
        "computation_options",
        "id",
        "node_visualization",
        "nodes",
        "pack_id",
        "properties",
    ]:
        assert required_key in rule
    assert rule["id"] == rule_id


def test_bi_rule(clients: ClientRegistry) -> None:
    rule = {
        "id": "some_rule",
        "pack_id": "default",
        "nodes": [
            {
                "search": {"type": "empty"},
                "action": {
                    "type": "state_of_service",
                    "host_regex": "$HOSTNAME$",
                    "service_regex": "ASM|ORACLE|proc",
                },
            }
        ],
        "params": {"arguments": ["HOSTNAME", "OTHERARGUMENT"]},
        "node_visualization": {"type": "none", "style_config": {}},
        "properties": {
            "title": "Applications",
            "comment": "",
            "docu_url": "",
            "icon": "",
            "state_messages": {},
        },
        "aggregation_function": {"type": "worst", "count": 1, "restrict_state": 2},
        "computation_options": {"disabled": False},
    }

    # create rule
    clients.BiRule.create(rule_id="some_rule", body=rule)

    # create dependent rule
    rule_dependent = rule.copy()
    rule_dependent["id"] = "dependent"
    rule_dependent["nodes"] = [
        {
            "search": {"type": "empty"},
            "action": {"type": "call_a_rule", "rule_id": "some_rule", "params": {"arguments": []}},
        }
    ]
    clients.BiRule.create(rule_id="dependent", body=rule_dependent)

    # try delete a rule, another rule is dependent on
    response = clients.BiRule.delete(rule_id="some_rule", expect_ok=False)
    response.assert_status_code(409)
    assert response.json == {
        "detail": "You cannot delete this rule: it is still used by other rules.",
        "status": 409,
        "title": "Conflict",
    }

    # delete dependent rule
    clients.BiRule.delete(rule_id="dependent", expect_ok=False)

    # delete rule
    clients.BiRule.delete(rule_id="some_rule", expect_ok=False)

    # delete non existing rule
    clients.BiRule.delete(rule_id="some_rule", expect_ok=False).assert_status_code(404)


def test_bi_aggregation(clients: ClientRegistry) -> None:
    aggregation = {
        "aggregation_visualization": {
            "ignore_rule_styles": False,
            "layout_id": "builtin_default",
            "line_style": "round",
        },
        "comment": "",
        "computation_options": {
            "disabled": True,
            "escalate_downtimes_as_warn": False,
            "use_hard_states": False,
        },
        "customer": None,
        "groups": {"names": ["Hosts"], "paths": []},
        "id": "some_aggregation",
        "node": {
            "action": {
                "params": {"arguments": ["$HOSTNAME$"]},
                "rule_id": "host",
                "type": "call_a_rule",
            },
            "search": {
                "conditions": {
                    "host_choice": {"type": "all_hosts"},
                    "host_folder": "",
                    "host_label_groups": [],
                    "host_tags": {"tcp": "tcp"},
                },
                "refer_to": "host",
                "type": "host_search",
            },
        },
        "pack_id": "default",
    }

    # create some aggregation
    clients.BiAggregation.create(
        aggregation_id="some_aggregation",
        body=aggregation,
    )

    # delete an aggregation
    clients.BiAggregation.delete(
        aggregation_id="some_aggregation",
    )

    # delete a non existing aggregation
    clients.BiAggregation.delete(
        aggregation_id="some_aggregation",
        expect_ok=False,
    ).assert_status_code(404)


def test_modify_bi_aggregation(clients: ClientRegistry) -> None:
    aggr_id = "default_aggregation"
    aggregation = clients.BiAggregation.get(aggregation_id=aggr_id).json
    assert aggregation["computation_options"]["disabled"]
    assert not aggregation["computation_options"]["escalate_downtimes_as_warn"]

    # Modify and send back
    aggregation["computation_options"]["disabled"] = False
    aggregation["computation_options"]["escalate_downtimes_as_warn"] = True
    clients.BiAggregation.edit(aggregation_id=aggr_id, body=aggregation)

    # Verify changed configuration
    aggregation = clients.BiAggregation.get(aggregation_id=aggr_id).json
    assert not aggregation["computation_options"]["disabled"]
    assert aggregation["computation_options"]["escalate_downtimes_as_warn"]


def test_modify_bi_rule(clients: ClientRegistry) -> None:
    rule_id = "applications"
    rule = clients.BiRule.get(rule_id=rule_id).json

    # Modify and send back
    rule["params"]["arguments"].append("OTHERARGUMENT")
    clients.BiRule.edit(rule_id=rule_id, body=rule)

    # Verify changed configuration
    rule = clients.BiRule.get(rule_id=rule_id).json
    assert "OTHERARGUMENT" in rule["params"]["arguments"]


def test_clone_bi_aggregation(clients: ClientRegistry) -> None:
    aggr_id = "default_aggregation"
    aggr = clients.BiAggregation.get(aggregation_id=aggr_id).json

    # Check invalid POST request on existing id
    clients.BiAggregation.create(
        aggregation_id=aggr_id, body=aggr, expect_ok=False
    ).assert_status_code(404)

    # Check invalid PUT request on new id
    clone_id = "cloned_aggregation"
    clients.BiAggregation.edit(
        aggregation_id=clone_id, body=aggr, expect_ok=False
    ).assert_status_code(404)

    # Save config under different id
    clients.BiAggregation.create(aggregation_id=clone_id, body=aggr)

    # Verify cloned_rule configuration
    cloned_aggr = clients.BiAggregation.get(aggregation_id=clone_id).json
    assert cloned_aggr["id"] == clone_id

    # Verify changed pack size
    pack = clients.BiPack.get(pack_id="default").json
    assert len(pack["members"]["aggregations"]["value"]) == 2


def test_clone_bi_rule(clients: ClientRegistry) -> None:
    rule_id = "applications"
    rule = clients.BiRule.get(rule_id=rule_id).json

    # Check invalid POST request on existing id
    clients.BiRule.create(
        rule_id=rule_id,
        body=rule,
        expect_ok=False,
    ).assert_status_code(404)

    # Check invalid PUT request on new id
    clone_id = "applications_clone"
    clients.BiRule.edit(
        rule_id=clone_id,
        body=rule,
        expect_ok=False,
    ).assert_status_code(404)

    # Save config under different id
    clients.BiRule.create(
        rule_id=clone_id,
        body=rule,
    )

    # Verify cloned_rule configuration
    cloned_rule = clients.BiRule.get(rule_id=clone_id).json
    assert cloned_rule["id"] == clone_id

    # Verify changed pack size
    pack = clients.BiPack.get(pack_id="default").json
    assert len(pack["members"]["rules"]["value"]) == 13


def test_clone_bi_pack(clients: ClientRegistry) -> None:
    pack_id = "default"
    pack = clients.BiPack.get(pack_id=pack_id).json
    new_data = {key: pack["extensions"][key] for key in ["title", "contact_groups", "public"]}
    new_data["title"] = "Test title"

    clients.BiPack.create(
        pack_id=pack_id,
        body=new_data,
        expect_ok=False,
    ).assert_status_code(404)

    # Check valid PUT request on existing id
    clients.BiPack.edit(
        pack_id=pack_id,
        body=new_data,
    )

    # Verify that rules/aggregations remain unchanged
    pack = clients.BiPack.get(pack_id=pack_id).json
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1
    assert pack["title"] == "Test title"

    # Check invalid PUT request on new id
    clone_id = "cloned_pack"
    clients.BiPack.edit(
        pack_id=clone_id,
        body=new_data,
        expect_ok=False,
    ).assert_status_code(404)

    # Save config under different id
    clients.BiPack.create(
        pack_id=clone_id,
        body=new_data,
    )

    # Verify cloned_pack configuration
    cloned_pack = clients.BiPack.get(pack_id=clone_id).json
    assert cloned_pack["id"] == clone_id

    # Verify that rules/aggregations have been migrated
    assert len(cloned_pack["members"]["rules"]["value"]) == 0
    assert len(cloned_pack["members"]["aggregations"]["value"]) == 0
    assert cloned_pack["title"] == "Test title"


def test_delete_pack(clients: ClientRegistry) -> None:
    pack_data = {
        "title": "Test pack",
        "contact_groups": [],
        "public": True,
    }

    # Create new pack
    clients.BiPack.create(
        pack_id="test_pack",
        body=pack_data,
    )

    # Verify creation
    pack = clients.BiPack.get(pack_id="test_pack").json
    assert pack["title"] == "Test pack"

    # Delete pack
    clients.BiPack.delete(pack_id="test_pack")

    # Verify deletion
    clients.BiPack.get(
        pack_id="test_pack",
        expect_ok=False,
    ).assert_status_code(404)


def test_delete_pack_forbidden(clients: ClientRegistry) -> None:
    clients.BiPack.delete(
        pack_id="default",
        expect_ok=False,
    ).assert_status_code(404)


def test_delete_non_existent_pack(clients: ClientRegistry) -> None:
    clients.BiPack.delete(
        pack_id="i-do-not-exist",
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_get_aggregation_state_empty(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    with live():
        with set_config(wato_enabled=wato_enabled):
            clients.BiAggregation.get_aggregation_state_post(body={})


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_get_aggregation_state_filter_names(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    with live():
        with set_config(wato_enabled=wato_enabled):
            clients.BiAggregation.get_aggregation_state_post(body={"filter_names": ["Host heute"]})


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_post_bi_pack_creating_contact_groups_regression(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
) -> None:
    contact_group = "i_should_never_exists"

    # Make sure the contact group does not exist
    clients.ContactGroup.get(
        group_id=contact_group,
        expect_ok=False,
    ).assert_status_code(404)

    # try to create it indirectly through posting it in a BI Pack,  unsuccessfully
    clients.BiPack.create(
        pack_id="testpack",
        body={"title": "my_cool_pack", "contact_groups": [contact_group], "public": False},
        expect_ok=False,
    ).assert_status_code(400)

    # Make sure it still does not exist
    clients.ContactGroup.get(
        group_id=contact_group,
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_get_aggregation_state_should_not_update_config_generation(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    generation_before_calling_endpoint = activate_changes._get_current_config_generation()

    with live():
        with set_config(wato_enabled=wato_enabled):
            clients.BiAggregation.get_aggregation_state_post(body={"filter_names": ["Host heute"]})

    generation_after_calling_endpoint = activate_changes._get_current_config_generation()

    assert generation_before_calling_endpoint == generation_after_calling_endpoint


def test_create_bi_aggregation_invalid_pack_id(clients: ClientRegistry) -> None:
    aggregation = {
        "aggregation_visualization": {
            "ignore_rule_styles": False,
            "layout_id": "builtin_default",
            "line_style": "round",
        },
        "comment": "",
        "computation_options": {
            "disabled": True,
            "escalate_downtimes_as_warn": False,
            "use_hard_states": False,
        },
        "customer": None,
        "groups": {"names": ["Hosts"], "paths": []},
        "id": "some_aggregation",
        "node": {
            "action": {
                "params": {"arguments": ["$HOSTNAME$"]},
                "rule_id": "host",
                "type": "call_a_rule",
            },
            "search": {
                "conditions": {
                    "host_choice": {"type": "all_hosts"},
                    "host_folder": "",
                    "host_label_groups": [],
                    "host_tags": {"tcp": "tcp"},
                },
                "refer_to": "host",
                "type": "host_search",
            },
        },
        "pack_id": "non-existing-pack-id",
    }

    resp = clients.BiAggregation.create(
        aggregation_id="some_aggregation",
        body=aggregation,
        expect_ok=False,
    )

    assert resp.json == {
        "title": "Not Found",
        "status": 404,
        "detail": "Unknown bi_pack: non-existing-pack-id",
    }


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_aggregation_state_empty_with_get_method(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    with live():
        with set_config(wato_enabled=wato_enabled):
            clients.BiAggregation.get_aggregation_state()


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_aggregation_state_filter_names_with_get_method(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    with live():
        with set_config(wato_enabled=wato_enabled):
            clients.BiAggregation.get_aggregation_state(
                query_params={"filter_names": ["Host heute"]}
            )


def create_bipack_get_rule_test_data(clients: ClientRegistry) -> dict:
    clients.BiPack.create(
        pack_id="Labeltest",
        body={"title": "Test title", "contact_groups": [], "public": True},
    )

    return {
        "pack_id": "Labeltest",
        "id": "label_test_rule_id_1",
        "nodes": [
            {
                "search": {
                    "type": "service_search",
                    "conditions": {
                        "host_folder": "",
                        "host_label_groups": [
                            {
                                "operator": "and",
                                "label_group": [
                                    {"operator": "and", "label": "mystery/switch:yes"},
                                    {"operator": "or", "label": "mystery/switch:no"},
                                ],
                            },
                            {
                                "operator": "or",
                                "label_group": [
                                    {"operator": "and", "label": "network/primary:yes"},
                                    {"operator": "not", "label": "network/primary:no"},
                                ],
                            },
                        ],
                        "host_tags": {},
                        "host_choice": {"type": "all_hosts"},
                        "service_regex": "(.*)",
                        "service_label_groups": [
                            {
                                "operator": "and",
                                "label_group": [
                                    {"operator": "and", "label": "network/stable:yes"},
                                    {"operator": "or", "label": "network/stable:no"},
                                ],
                            },
                            {
                                "operator": "or",
                                "label_group": [
                                    {"operator": "and", "label": "network/uplink:yes"},
                                    {"operator": "not", "label": "network/uplink:no"},
                                ],
                            },
                        ],
                    },
                },
                "action": {"type": "state_of_service", "host_regex": "$1$", "service_regex": "$2$"},
            }
        ],
        "params": {"arguments": []},
        "node_visualization": {"type": "block", "style_config": {}},
        "properties": {
            "title": "Labeltest 2.3.0 UI",
            "comment": "",
            "docu_url": "",
            "icon": "",
            "state_messages": {},
        },
        "aggregation_function": {"type": "worst", "count": 1, "restrict_state": 2},
        "computation_options": {"disabled": False},
    }


def test_create_rule_with_label_groups(clients: ClientRegistry) -> None:
    test_rule = create_bipack_get_rule_test_data(clients)
    resp = clients.BiRule.create(rule_id="label_test_rule_id_1", body=test_rule)
    assert (
        resp.json["nodes"][0]["search"]["conditions"]
        == test_rule["nodes"][0]["search"]["conditions"]
    )


def test_create_rule_with_label_groups_no_first_operator(clients: ClientRegistry) -> None:
    test_rule = create_bipack_get_rule_test_data(clients)
    del test_rule["nodes"][0]["search"]["conditions"]["host_label_groups"][0]["operator"]
    del test_rule["nodes"][0]["search"]["conditions"]["service_label_groups"][0]["operator"]
    clients.BiRule.create(rule_id="label_test_rule_id_1", body=test_rule)
