#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import os

import pytest

from cmk.utils import paths
from cmk.utils.store import load_mk_file


@pytest.fixture(scope="function", name="new_rule")
def new_rule_fixture(logged_in_admin_wsgi_app):
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values = {
        "ruleset": "inventory_df_rules",
        "folder": "/",
        "properties": {
            "description": "This is my title for this very important rule.",
            "comment": "They made me do it!",
            "documentation_url": "http://example.com/",
            "disabled": False,
        },
        "value_raw": """{
            "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
            "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
        }""",
        "conditions": {
            "host_tag": [
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
            "host_label": [{"key": "os", "operator": "is", "value": "windows"}],
        },
    }
    resp = wsgi_app.post(
        base + "/domain-types/rule/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(values),
    )
    return values, resp


def test_openapi_create_rule_regression(logged_in_admin_wsgi_app):
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


def test_openapi_create_rule_failure(logged_in_admin_wsgi_app):
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


def test_openapi_create_rule(logged_in_admin_wsgi_app, new_rule):
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values, new_resp = new_rule

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


def test_create_rule_with_bool_value(base: str, logged_in_admin_wsgi_app) -> None:
    wsgi_app = logged_in_admin_wsgi_app
    resp = wsgi_app.post(
        f"{base}/domain-types/rule/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(
            {
                "ruleset": "ignored_services",
                "folder": "/",
                "properties": {
                    "description": "Test",
                    "disabled": False,
                },
                "value_raw": "True",
                "conditions": {},
            }
        ),
    )

    assert resp.json["extensions"]["value_raw"] == "True"


def test_openapi_list_rules(logged_in_admin_wsgi_app, new_rule):
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values, _ = new_rule
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
    assert stored["conditions"]["host_label"] == values["conditions"]["host_label"]
    assert stored["conditions"]["host_tag"] == values["conditions"]["host_tag"]


def test_openapi_delete_rule(logged_in_admin_wsgi_app, new_rule):
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values, resp = new_rule

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


def test_openapi_show_ruleset(logged_in_admin_wsgi_app):
    wsgi_app = logged_in_admin_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + "/objects/ruleset/host_groups",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert resp.json["extensions"]["name"] == "host_groups"


def test_openapi_list_rulesets(logged_in_admin_wsgi_app):
    wsgi_app = logged_in_admin_wsgi_app

    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + "/domain-types/ruleset/collections/all?fulltext=cisco_qos",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert len(resp.json["value"]) == 2
