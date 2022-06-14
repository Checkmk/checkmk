#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import os
import typing
import urllib

import pytest
import webtest  # type: ignore[import]

from cmk.utils import paths
from cmk.utils.store import load_mk_file


@pytest.fixture(scope="function", name="new_rule")
def new_rule_fixture(logged_in_admin_wsgi_app):
    return _create_rule(
        logged_in_admin_wsgi_app,
        folder="/",
        comment="They made me do it!",
        description="This is my title for this very important rule.",
        documentation_url="http://example.com/",
    )


def _create_rule(
    wsgi_app,
    folder,
    comment="",
    description="",
    documentation_url="",
    disabled=False,
) -> tuple[webtest.TestResponse, dict[str, typing.Any]]:
    base = "/NO_SITE/check_mk/api/1.0"
    properties = {
        "description": description,
        "comment": comment,
        "disabled": disabled,
    }
    if documentation_url:
        properties["documentation_url"] = documentation_url
    values = {
        "ruleset": "inventory_df_rules",
        "folder": folder,
        "properties": properties,
        "value_raw": """{
            "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
            "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
        }""",
        "conditions": {
            "host_tags": [
                {
                    "key": "criticality",
                    "operator": "is",
                    "value": "prod",
                },
                {
                    "key": "networking",
                    "operator": "is_not",
                    "value": "wan",
                },
            ],
            "host_labels": [{"key": "os", "operator": "is", "value": "windows"}],
        },
    }
    resp = wsgi_app.post(
        base + "/domain-types/rule/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(values),
    )
    return resp, values


@pytest.fixture(scope="function", name="test_folders")
def site_with_test_folders(wsgi_app, base):
    test_folder_name_one = "test_folder_1"
    test_folder_name_two = "test_folder_2"

    _create_folder(wsgi_app, base, test_folder_name_one)
    _create_folder(wsgi_app, base, test_folder_name_two)

    return test_folder_name_one, test_folder_name_two


def _create_folder(wsgi_app, base, folder_name, parent="/"):
    return wsgi_app.post(
        base + "/domain-types/folder_config/collections/all",
        params=json.dumps(
            {
                "name": folder_name,
                "title": folder_name,
                "parent": parent,
            }
        ),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        status=200,
    )


def test_openapi_create_rule_regression(logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"
    values = {
        "ruleset": "checkgroup_parameters:filesystem",
        "folder": "~",
        "properties": {"disabled": False, "description": "API2I"},
        "value_raw": '{"inodes_levels": (10.0, 5.0), "levels": [(0, (0, 0)), (0, (0.0, 0.0))], "magic": 0.8, "trend_perfdata": True}',
        "conditions": {},
    }
    _ = wsgi_app.post(
        base + "/domain-types/rule/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(values),
        status=200,
    )


def test_openapi_rules_href_escaped(logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + "/domain-types/ruleset/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        status=200,
    )
    ruleset = next(r for r in resp.json["value"] if "special_agents:gcp" == r["id"])
    assert (
        ruleset["links"][0]["href"]
        == "http://localhost/NO_SITE/check_mk/api/1.0/objects/ruleset/special_agents%253Agcp"
    )


def test_openapi_create_rule_failure(logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values = {
        "ruleset": "host_groups",
        "folder": "~",
        "properties": {
            "description": "This is my title for this very important rule.",
            "comment": "They made me do it!",
            "documentation_url": "http://example.com/",
            "disabled": False,
        },
        "value_raw": "{}",
        "conditions": {},
    }
    resp = wsgi_app.post(
        base + "/domain-types/rule/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(values),
        status=400,
    )
    # Its not really important that this text is in the response, just that this call failed.
    assert "You have not defined any host group yet" in resp.json["detail"]


def test_openapi_create_rule(logged_in_admin_wsgi_app, new_rule) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    new_resp, values = new_rule

    resp = wsgi_app.get(
        base + f"/objects/ruleset/{values['ruleset']}",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json["extensions"]["number_of_rules"] == 1

    # Also fetch the newly created rule and check if it's actually persisted.
    resp = wsgi_app.get(
        base + f"/objects/rule/{new_resp.json['id']}",
        headers={"Accept": "application/json"},
        status=200,
    )
    ext = resp.json["extensions"]
    assert ext["ruleset"] == values["ruleset"]
    assert ext["folder"] == values["folder"]
    assert ext["properties"] == values["properties"]
    assert ext["conditions"].items() >= values["conditions"].items()

    # Check that the format on disk is as expected.
    rules_mk = os.path.join(paths.omd_root, "etc", "check_mk", "conf.d", "wato", "rules.mk")
    environ = load_mk_file(rules_mk, default={})
    stored_condition = environ[values["ruleset"]][0]["condition"]
    expected_condition = {
        "host_tags": {"criticality": "prod", "networking": {"$ne": "wan"}},
        "host_labels": {"os": "windows"},
    }
    assert stored_condition == expected_condition


def test_create_rule_with_string_value(logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    resp = wsgi_app.post(
        base + "/domain-types/rule/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(
            {
                "ruleset": "extra_host_conf:notification_options",
                "folder": "/",
                "properties": {
                    "description": "Test",
                    "disabled": False,
                },
                "value_raw": "'d,u,r,f,s'",
                "conditions": {},
            }
        ),
    )

    assert resp.json["extensions"]["value_raw"] == "'d,u,r,f,s'"


def test_openapi_list_rules(logged_in_admin_wsgi_app, new_rule) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    _, values = new_rule
    rule_set = values["ruleset"]

    resp = wsgi_app.get(
        base + f"/domain-types/rule/collections/all?ruleset_name={rule_set}",
        headers={"Accept": "application/json"},
        status=200,
    )

    for entry in resp.json["value"]:
        assert entry["domainType"] == "rule"

    stored = resp.json["value"][0]["extensions"]
    assert stored["properties"]["disabled"] == values["properties"]["disabled"]
    assert stored["properties"]["comment"] == values["properties"]["comment"]
    # Do the complete round-trip check. Everything stored is also retrieved.
    assert stored["conditions"]["host_labels"] == values["conditions"]["host_labels"]
    assert stored["conditions"]["host_tags"] == values["conditions"]["host_tags"]


def test_openapi_delete_rule(logged_in_admin_wsgi_app, new_rule) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    resp, values = new_rule

    _resp = wsgi_app.get(
        base + f"/objects/ruleset/{values['ruleset']}",
        headers={"Accept": "application/json"},
    )
    assert _resp.json["extensions"]["number_of_rules"] == 1

    wsgi_app.follow_link(
        resp,
        ".../delete",
        status=204,
        headers={"Accept": "application/json"},
    )

    list_resp = wsgi_app.get(
        base + f"/objects/ruleset/{values['ruleset']}",
        headers={"Accept": "application/json"},
    )
    assert list_resp.json["extensions"]["number_of_rules"] == 0

    wsgi_app.follow_link(
        resp,
        ".../delete",
        status=404,
        headers={"Accept": "application/json"},
    )


@pytest.mark.parametrize("ruleset", ["host_groups", "special_agents:gcp"])
def test_openapi_show_ruleset(logged_in_admin_wsgi_app, ruleset) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + f"/objects/ruleset/{urllib.parse.quote(ruleset)}",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert resp.json["extensions"]["name"] == ruleset


def test_openapi_show_non_existing_ruleset(logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"
    # Request a ruleset that doesn't exist should return a 400 Bad Request.
    wsgi_app.get(
        base + "/objects/ruleset/non_existing_ruleset",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        status=404,
    )


def test_openapi_list_rulesets(logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app

    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + "/domain-types/ruleset/collections/all?fulltext=cisco_qos",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert len(resp.json["value"]) == 2


def test_openapi_has_rule(aut_user_auth_wsgi_app, base, new_rule, test_folders) -> None:
    wsgi_app = aut_user_auth_wsgi_app
    assert _order_of_rules(wsgi_app, base) == ["They made me do it!"]


def test_openapi_create_rule_order(aut_user_auth_wsgi_app, base, new_rule, test_folders) -> None:
    wsgi_app = aut_user_auth_wsgi_app
    folder_name_one, folder_name_two = test_folders
    rule1, _ = _create_rule(wsgi_app, f"/{folder_name_one}", comment="rule1")
    rule1_id = rule1.json["id"]

    assert _order_of_rules(wsgi_app, base) == ["rule1", "They made me do it!"]

    rule2, _ = _create_rule(wsgi_app, f"/{folder_name_two}", comment="rule2")
    rule2_id = rule2.json["id"]

    assert _order_of_rules(wsgi_app, base) == ["rule2", "rule1", "They made me do it!"]

    _ensure_on_folder(wsgi_app, base, rule1_id, f"/{folder_name_one}")
    _ensure_on_folder(wsgi_app, base, rule2_id, f"/{folder_name_two}")


def test_openapi_move_rule_to_top_of_folder(
    aut_user_auth_wsgi_app, base, new_rule, test_folders
) -> None:
    wsgi_app = aut_user_auth_wsgi_app
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(wsgi_app, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(wsgi_app, f"/{folder_name_two}", comment="rule2")

    _move_to(wsgi_app, base, rule_id, "top_of_folder", folder=f"/{folder_name_one}")
    _ensure_on_folder(wsgi_app, base, rule_id, f"/{folder_name_one}")
    assert _order_of_rules(wsgi_app, base) == ["rule2", "They made me do it!", "rule1"]


def test_openapi_move_rule_to_bottom_of_folder(
    aut_user_auth_wsgi_app, base, new_rule, test_folders
):
    wsgi_app = aut_user_auth_wsgi_app
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(wsgi_app, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(wsgi_app, f"/{folder_name_two}", comment="rule2")

    _move_to(wsgi_app, base, rule_id, "bottom_of_folder", folder=f"/{folder_name_two}")
    _ensure_on_folder(wsgi_app, base, rule_id, f"/{folder_name_two}")

    assert _order_of_rules(wsgi_app, base) == ["rule2", "They made me do it!", "rule1"]


def test_openapi_move_rule_after_specific_rule(
    aut_user_auth_wsgi_app, base, new_rule, test_folders
):
    wsgi_app = aut_user_auth_wsgi_app
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    rule1, _ = _create_rule(wsgi_app, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(wsgi_app, f"/{folder_name_two}", comment="rule2")

    _move_to(wsgi_app, base, rule_id, "after_specific_rule", dest_rule_id=rule1.json["id"])
    _ensure_on_folder(wsgi_app, base, rule_id, f"/{folder_name_one}")

    assert _order_of_rules(wsgi_app, base) == ["rule2", "rule1", "They made me do it!"]


def test_openapi_move_rule_before_specific_rule(
    aut_user_auth_wsgi_app, base, new_rule, test_folders
):
    wsgi_app = aut_user_auth_wsgi_app
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(wsgi_app, f"/{folder_name_one}", comment="rule1")
    rule2, _ = _create_rule(wsgi_app, f"/{folder_name_two}", comment="rule2")

    _move_to(wsgi_app, base, rule_id, "before_specific_rule", dest_rule_id=rule2.json["id"])
    _ensure_on_folder(wsgi_app, base, rule_id, f"/{folder_name_two}")

    assert _order_of_rules(wsgi_app, base) == ["They made me do it!", "rule2", "rule1"]


def _ensure_on_folder(wsgi_app, base, _rule_id, folder):
    rule_resp = wsgi_app.get(
        base + f"/objects/rule/{_rule_id}",
        headers={"Accept": "application/json"},
    )
    assert rule_resp.json["extensions"]["folder"] == folder


def _move_to(wsgi_app, base, _rule_id, position, dest_rule_id=None, folder=None):
    options = {"position": position}
    if position in ("top_of_folder", "bottom_of_folder"):
        options["folder"] = folder
    elif position in ("before_specific_rule", "after_specific_rule"):
        options["rule_id"] = dest_rule_id

    _resp = wsgi_app.post(
        base + f"/objects/rule/{_rule_id}/actions/move/invoke",
        params=json.dumps(options),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        status=200,
    )

    if position in ("top_of_folder", "bottom_of_folder"):
        assert _resp.json["extensions"]["folder"] == folder

    return _resp


def _order_of_rules(wsgi_app, base) -> list[str]:
    _resp = wsgi_app.get(
        base + "/domain-types/rule/collections/all?ruleset_name=inventory_df_rules",
        headers={"Accept": "application/json"},
        status=200,
    )
    comments = []
    for rule in _resp.json["value"]:
        comments.append(rule["extensions"]["properties"]["comment"])
    return comments
