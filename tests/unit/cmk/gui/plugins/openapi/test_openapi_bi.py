#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_openapi_get_bi_packs(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    response = aut_user_auth_wsgi_app.get(
        base + "/domain-types/bi_pack/collections/all",
        headers={"Accept": "application/json"},
    )
    packs = json.loads(response.text)
    assert packs["domainType"] == "bi_pack"
    assert len(packs["value"]) == 1
    assert packs["value"][0]["title"] == "Default Pack"


def test_openapi_get_bi_rule_non_existing_id(base: str, aut_user_auth_wsgi_app: WebTestAppForCMK):
    aut_user_auth_wsgi_app.get(
        base + "/domain-types/objects/bi_rule/abc",
        headers={"Accept": "application/json"},
        status=404,
    )


def test_openapi_get_bi_aggregation_non_existing_id(
    base: str, aut_user_auth_wsgi_app: WebTestAppForCMK
):
    aut_user_auth_wsgi_app.get(
        base + "/domain-types/objects/bi_aggregation/abc",
        headers={"Accept": "application/json"},
        status=404,
    )


def test_openapi_get_bi_pack(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    pack_id = "default"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/%s" % pack_id, headers={"Accept": "application/json"}, status=200
    )
    pack = json.loads(response.text)
    assert pack["id"] == pack_id
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1


def test_openapi_get_bi_aggregation(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    aggr_id = "default_aggregation"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_aggregation/%s" % aggr_id,
        headers={"Accept": "application/json"},
        status=200,
    )
    aggregation = json.loads(response.text)
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


def test_openapi_get_bi_rule(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    rule_id = "applications"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_rule/%s" % rule_id, headers={"Accept": "application/json"}, status=200
    )
    rule = json.loads(response.text)
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


def test_openapi_bi_rule(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
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
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_rule/some_rule",
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
        params=json.dumps(rule),
    )

    # create dependent rule
    rule_dependent = rule.copy()
    rule_dependent["id"] = "dependent"
    rule_dependent["nodes"] = [
        {
            "search": {"type": "empty"},
            "action": {"type": "call_a_rule", "rule_id": "some_rule", "params": {"arguments": []}},
        }
    ]
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_rule/dependent",
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
        params=json.dumps(rule_dependent),
    )

    # try delete a rule, another rule is dependent on
    response = aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_rule/some_rule",
        headers={"Accept": "application/json"},
        status=409,
    )
    assert json.loads(response.text) == {
        "detail": "You cannot delete this rule: it is still used by other rules.",
        "status": 409,
        "title": "Conflict",
    }

    # delete dependent rule
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_rule/dependent",
        headers={"Accept": "application/json"},
        status=204,
    )

    # delete rule
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_rule/some_rule",
        headers={"Accept": "application/json"},
        status=204,
    )

    # delete non existing rule
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_rule/some_rule",
        headers={"Accept": "application/json"},
        status=404,
    )


def test_openapi_bi_aggregation(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

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
                    "host_labels": {},
                    "host_tags": {"tcp": "tcp"},
                },
                "refer_to": "host",
                "type": "host_search",
            },
        },
        "pack_id": "default",
    }

    # create some aggregation
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_aggregation/some_aggregation",
        content_type="application/json",
        headers={"Accept": "application/json"},
        params=json.dumps(aggregation),
        status=200,
    )

    # delete an aggregation
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_aggregation/some_aggregation",
        headers={"Accept": "application/json"},
        status=204,
    )

    # delete a non existing aggregation
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_aggregation/some_aggregation",
        headers={"Accept": "application/json"},
        status=404,
    )


def test_openapi_modify_bi_aggregation(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    aggr_id = "default_aggregation"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_aggregation/%s" % aggr_id,
        headers={"Accept": "application/json"},
        status=200,
    )
    aggregation = json.loads(response.text)
    assert aggregation["computation_options"]["disabled"]
    assert not aggregation["computation_options"]["escalate_downtimes_as_warn"]

    # Modify and send back
    aggregation["computation_options"]["disabled"] = False
    aggregation["computation_options"]["escalate_downtimes_as_warn"] = True
    aut_user_auth_wsgi_app.put(
        base + "/objects/bi_aggregation/%s" % aggr_id,
        content_type="application/json",
        params=json.dumps(aggregation),
        headers={"Accept": "application/json"},
        status=200,
    )

    # Verify changed configuration
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_aggregation/%s" % aggr_id,
        headers={"Accept": "application/json"},
        status=200,
    )
    aggregation = json.loads(response.text)
    assert not aggregation["computation_options"]["disabled"]
    assert aggregation["computation_options"]["escalate_downtimes_as_warn"]


def test_openapi_modify_bi_rule(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    rule_id = "applications"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_rule/%s" % rule_id, headers={"Accept": "application/json"}, status=200
    )
    rule = json.loads(response.text)
    rule["params"]["arguments"].append("OTHERARGUMENT")

    # Modify and send back
    aut_user_auth_wsgi_app.put(
        base + "/objects/bi_rule/%s" % rule_id,
        content_type="application/json",
        params=json.dumps(rule),
        status=200,
        headers={"Accept": "application/json"},
    )

    # Verify changed configuration
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_rule/%s" % rule_id, headers={"Accept": "application/json"}, status=200
    )
    rule = json.loads(response.text)
    assert "OTHERARGUMENT" in rule["params"]["arguments"]


def test_openapi_clone_bi_aggregation(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    aggr_id = "default_aggregation"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_aggregation/%s" % aggr_id,
        headers={"Accept": "application/json"},
        status=200,
    )
    aggr = json.loads(response.text)

    clone_id = "cloned_aggregation"

    # Check invalid POST request on existing id
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_aggregation/%s" % aggr_id,
        content_type="application/json",
        headers={"Accept": "application/json"},
        params=json.dumps(aggr),
        status=404,
    )

    # Check invalid PUT request on new id
    aut_user_auth_wsgi_app.put(
        base + "/objects/bi_aggregation/%s" % clone_id,
        content_type="application/json",
        params=json.dumps(aggr),
        headers={"Accept": "application/json"},
        status=404,
    )

    # Save config under different id
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_aggregation/%s" % clone_id,
        content_type="application/json",
        params=json.dumps(aggr),
        headers={"Accept": "application/json"},
        status=200,
    )

    # Verify cloned_rule configuration
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_aggregation/%s" % clone_id,
        headers={"Accept": "application/json"},
        status=200,
    )
    cloned_aggr = json.loads(response.text)
    assert cloned_aggr["id"] == clone_id

    # Verify changed pack size
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/default", headers={"Accept": "application/json"}, status=200
    )
    pack = json.loads(response.text)
    assert len(pack["members"]["aggregations"]["value"]) == 2


def test_openapi_clone_bi_rule(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    rule_id = "applications"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_rule/%s" % rule_id, headers={"Accept": "application/json"}, status=200
    )
    rule = json.loads(response.text)

    clone_id = "applications_clone"

    # Check invalid POST request on existing id
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_rule/%s" % rule_id,
        content_type="application/json",
        params=json.dumps(rule),
        headers={"Accept": "application/json"},
        status=404,
    )

    # Check invalid PUT request on new id
    aut_user_auth_wsgi_app.put(
        base + "/objects/bi_rule/%s" % clone_id,
        content_type="application/json",
        params=json.dumps(rule),
        headers={"Accept": "application/json"},
        status=404,
    )

    # Save config under different id
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_rule/%s" % clone_id,
        content_type="application/json",
        params=json.dumps(rule),
        headers={"Accept": "application/json"},
        status=200,
    )

    # Verify cloned_rule configuration
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_rule/%s" % clone_id, headers={"Accept": "application/json"}, status=200
    )
    cloned_rule = json.loads(response.text)
    assert cloned_rule["id"] == clone_id

    # Verify changed pack size
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/default", headers={"Accept": "application/json"}, status=200
    )
    pack = json.loads(response.text)
    assert len(pack["members"]["rules"]["value"]) == 13


def test_openapi_clone_bi_pack(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    pack_id = "default"
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/%s" % pack_id, headers={"Accept": "application/json"}, status=200
    )
    pack = json.loads(response.text)

    clone_id = "cloned_pack"
    new_data = {key: pack["extensions"][key] for key in ["title", "contact_groups", "public"]}
    new_data["title"] = "Test title"

    # Check invalid POST request on existing id
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_pack/%s" % pack_id,
        content_type="application/json",
        params=json.dumps(new_data),
        headers={"Accept": "application/json"},
        status=404,
    )

    # Check valid PUT request on existing id
    aut_user_auth_wsgi_app.put(
        base + "/objects/bi_pack/%s" % pack_id,
        content_type="application/json",
        params=json.dumps(new_data),
        headers={"Accept": "application/json"},
        status=200,
    )

    # Verify that rules/aggregations remain unchanged
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/%s" % pack_id, headers={"Accept": "application/json"}, status=200
    )
    pack = json.loads(response.text)
    assert len(pack["members"]["rules"]["value"]) == 12
    assert len(pack["members"]["aggregations"]["value"]) == 1
    assert pack["title"] == "Test title"

    # Check invalid PUT request on new id
    aut_user_auth_wsgi_app.put(
        base + "/objects/bi_pack/%s" % clone_id,
        content_type="application/json",
        params=json.dumps(new_data),
        headers={"Accept": "application/json"},
        status=404,
    )

    # Save config under different id
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_pack/%s" % clone_id,
        content_type="application/json",
        params=json.dumps(new_data),
        headers={"Accept": "application/json"},
        status=200,
    )

    # Verify cloned_pack configuration
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/%s" % clone_id, headers={"Accept": "application/json"}, status=200
    )
    cloned_pack = json.loads(response.text)
    assert cloned_pack["id"] == clone_id

    # Verify that rules/aggregations have been migrated
    assert len(cloned_pack["members"]["rules"]["value"]) == 0
    assert len(cloned_pack["members"]["aggregations"]["value"]) == 0
    assert cloned_pack["title"] == "Test title"


def test_openapi_delete_pack(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"

    pack_data = {
        "title": "Test pack",
        "contact_groups": [],
        "public": True,
    }

    # Create new pack
    aut_user_auth_wsgi_app.post(
        base + "/objects/bi_pack/test_pack",
        content_type="application/json",
        params=json.dumps(pack_data),
        headers={"Accept": "application/json"},
        status=200,
    )

    # Verify creation
    response = aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/test_pack", headers={"Accept": "application/json"}, status=200
    )
    pack = json.loads(response.text)
    assert pack["title"] == "Test pack"

    # Delete pack
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_pack/test_pack", headers={"Accept": "application/json"}, status=204
    )

    # Verify deletion
    aut_user_auth_wsgi_app.get(
        base + "/objects/bi_pack/test_pack", headers={"Accept": "application/json"}, status=404
    )


def test_openapi_delete_pack_forbidden(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"
    aut_user_auth_wsgi_app.delete(
        base + "/objects/bi_pack/default",
        content_type="application/json",
        headers={"Accept": "application/json"},
        status=404,
    )


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_get_aggregation_state_empty(  # type:ignore[no-untyped-def]
    aut_user_auth_wsgi_app, mock_livestatus, wato_enabled
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    postfix = "/domain-types/bi_aggregation/actions/aggregation_state/invoke"
    url = f"{base}{postfix}"

    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    with live():
        with aut_user_auth_wsgi_app.set_config(wato_enabled=wato_enabled):
            _response = aut_user_auth_wsgi_app.post(
                url,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                status=200,
                params=json.dumps({}),
            )


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_get_aggregation_state_filter_names(  # type:ignore[no-untyped-def]
    aut_user_auth_wsgi_app, mock_livestatus, wato_enabled
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    postfix = "/domain-types/bi_aggregation/actions/aggregation_state/invoke"
    url = f"{base}{postfix}"

    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias host_filename"
    )

    with live():
        with aut_user_auth_wsgi_app.set_config(wato_enabled=wato_enabled):
            _response = aut_user_auth_wsgi_app.post(
                url,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                status=200,
                params=json.dumps({"filter_names": ["Host heute"]}),
            )


@pytest.mark.parametrize("wato_enabled", [True, False])
def test_post_bi_pack_creating_contact_groups_regression(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    wato_enabled: bool,
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    contact_group = "i_should_never_exists"
    contact_group_url = f"{base}/objects/contact_group_config/{contact_group}"

    # Make sure the contact group does not exist
    aut_user_auth_wsgi_app.get(
        url=contact_group_url,
        status=404,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    # try to create it indirectly through posting it in a BI Pack,  unsuccessfully
    aut_user_auth_wsgi_app.post(
        url=f"{base}/objects/bi_pack/testpack",
        params=json.dumps(
            {"title": "my_cool_pack", "contact_groups": [contact_group], "public": False}
        ),
        status=400,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    # Make sure it still does not exist
    aut_user_auth_wsgi_app.get(
        url=contact_group_url,
        status=404,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
