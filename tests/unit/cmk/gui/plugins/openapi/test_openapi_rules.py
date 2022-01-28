#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import pytest


@pytest.fixture(scope="function", name="new_rule")
def new_rule_fixture(logged_in_wsgi_app):
    wsgi_app = logged_in_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values = {
        "ruleset": "inventory_df_rules",
        "folder": "~",
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
        base + "/domain-types/ruleset/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(values),
    )
    return values, resp


def test_openapi_create_rule_failure(logged_in_wsgi_app):
    wsgi_app = logged_in_wsgi_app
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
        base + "/domain-types/ruleset/collections/all",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        params=json.dumps(values),
        status=400,
    )
    assert "You have not defined any host group yet." in resp.json["detail"]


def test_openapi_create_rule(logged_in_wsgi_app, new_rule):
    wsgi_app = logged_in_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values, _ = new_rule

    resp = wsgi_app.get(
        base + f"/objects/ruleset/{values['ruleset']}",
        headers={"Accept": "application/json"},
    )
    assert resp.json["extensions"]["number_of_rules"] == 1


def test_openapi_list_rules(logged_in_wsgi_app, new_rule):
    wsgi_app = logged_in_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"

    values, _ = new_rule
    rule_set = values["ruleset"]

    resp = wsgi_app.get(
        base + f"/domain-types/rule/collections/{rule_set}",
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


def test_openapi_delete_rule(logged_in_wsgi_app, new_rule):
    wsgi_app = logged_in_wsgi_app
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


def test_openapi_show_ruleset(logged_in_wsgi_app):
    wsgi_app = logged_in_wsgi_app
    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + "/objects/ruleset/host_groups",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert resp.json["extensions"]["name"] == "host_groups"


def test_openapi_list_rulesets(logged_in_wsgi_app):
    wsgi_app = logged_in_wsgi_app

    base = "/NO_SITE/check_mk/api/1.0"
    resp = wsgi_app.get(
        base + "/domain-types/ruleset/collections/all?fulltext=aws",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert len(resp.json["value"]) == 77
