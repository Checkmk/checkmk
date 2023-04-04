#!/usr/bin/env python3
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import random
import string
import typing
import urllib
from typing import Any

import pytest
from webtest import TestResponse  # type: ignore[import]

from tests.testlib.rest_api_client import (
    ContactGroupTestClient,
    Response,
    RestApiClient,
    RuleConditions,
    RuleProperties,
    RulesetTestClient,
    RulesTestClient,
)

from cmk.utils import paths
from cmk.utils.store import load_mk_file
from cmk.utils.type_defs import UserId

import cmk.gui.watolib.check_mk_automations
import cmk.gui.watolib.rulespecs


@pytest.fixture(scope="function", name="new_rule")
def new_rule_fixture(rule_client: RulesTestClient) -> tuple[TestResponse, dict[str, Any]]:
    return _create_rule(
        rule_client,
        folder="/",
        comment="They made me do it!",
        description="This is my title for this very important rule.",
        documentation_url="http://example.com/",
    )


def _create_rule(
    rule_client: RulesTestClient,
    folder: str,
    comment: str = "",
    description: str = "",
    documentation_url: str = "",
    disabled: bool = False,
    ruleset: str = "inventory_df_rules",
    value: dict[str, Any] | list[Any] | tuple | str | None = None,
    value_raw: str = """{
        "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
        "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
    }""",
) -> tuple[TestResponse, dict[str, Any]]:
    if value is None:
        value = {
            "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
            "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
        }

    properties: RuleProperties = {
        "description": description,
        "comment": comment,
        "disabled": disabled,
    }
    if documentation_url:
        properties["documentation_url"] = documentation_url

    conditions: RuleConditions = {
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
    }

    values = {
        "ruleset": ruleset,
        "folder": folder,
        "properties": properties,
        "value_raw": value_raw,
        "conditions": conditions,
    }

    resp = rule_client.create(
        ruleset=ruleset,
        folder=folder,
        properties=properties,
        value_raw=value_raw,
        conditions=conditions,
    )
    return resp, values


@pytest.fixture(scope="function", name="test_folders")
def site_with_test_folders(api_client: RestApiClient) -> tuple[str, str]:
    test_folder_name_one = "test_folder_1"
    test_folder_name_two = "test_folder_2"

    api_client.create_folder(
        folder_name=test_folder_name_one,
        title=test_folder_name_one,
        parent="/",
        expect_ok=True,
    )
    api_client.create_folder(
        folder_name=test_folder_name_two,
        title=test_folder_name_two,
        parent="/",
        expect_ok=True,
    )

    return test_folder_name_one, test_folder_name_two


def test_openapi_get_non_existing_rule(rule_client: RulesTestClient) -> None:
    rule_client.get(rule_id="non_existing_rule_id", expect_ok=False).assert_status_code(404)


def test_openapi_create_rule_regression(rule_client: RulesTestClient) -> None:
    value_raw = '{"inodes_levels": (10.0, 5.0), "levels": [(0, (0, 0)), (0, (0.0, 0.0))], "magic": 0.8, "trend_perfdata": True}'
    rule_client.create(
        ruleset="checkgroup_parameters:filesystem",
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False, "description": "API2I"},
    )


def test_openapi_value_raw_is_unaltered(rule_client: RulesTestClient) -> None:
    value_raw = "{'levels': (10.0, 5.0)}"
    resp = rule_client.create(
        ruleset="checkgroup_parameters:memory_percentage_used",
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False},
    )
    resp2 = rule_client.get(rule_id=resp.json["id"])
    assert value_raw == resp2.json["extensions"]["value_raw"]


def test_openapi_value_active_check_http(rule_client: RulesTestClient) -> None:
    value_raw = """{
        "name": "Halli-gALLI",
        "host": {"address": "mimi.ch", "virthost": "mimi.ch"},
        "mode": (
            "url",
            {
                "uri": "/lala/misite.html",
                "ssl": "auto",
                "expect_string": "status:UP",
                "urlize": True,
            },
        ),
    }"""
    resp = rule_client.create(
        ruleset="active_checks:http",
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False},
    )

    rule_client.get(rule_id=resp.json["id"])


def test_openapi_rules_href_escaped(ruleset_client: RulesetTestClient) -> None:
    resp = ruleset_client.get_all(search_options="?used=0")
    ruleset = next(r for r in resp.json["value"] if "special_agents:gcp" == r["id"])
    assert (
        ruleset["links"][0]["href"]
        == "http://localhost/NO_SITE/check_mk/api/1.0/objects/ruleset/special_agents%253Agcp"
    )


def test_openapi_create_rule_failure(rule_client: RulesTestClient) -> None:
    resp = rule_client.create(
        ruleset="host_groups",
        folder="~",
        properties={
            "description": "This is my title for this very important rule.",
            "comment": "They made me do it!",
            "documentation_url": "http://example.com/",
            "disabled": False,
        },
        value_raw="{}",
        conditions={},
        expect_ok=False,
    )
    resp.assert_status_code(400)

    # Its not really important that this text is in the response, just that this call failed.
    # assert "You have not defined any host group yet" in resp.json["detail"]


def test_openapi_create_rule(
    rule_client: RulesTestClient,
    ruleset_client: RulesetTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
) -> None:
    new_resp, values = new_rule

    resp = ruleset_client.get(ruleset_id=values["ruleset"])
    assert resp.json["extensions"]["number_of_rules"] == 1

    # Also fetch the newly created rule and check if it's actually persisted.
    resp2 = rule_client.get(new_resp.json["id"])
    ext = resp2.json["extensions"]
    assert ext["ruleset"] == values["ruleset"]
    assert ext["folder"] == values["folder"]
    assert ext["properties"] == values["properties"]
    assert ext["conditions"].items() >= values["conditions"].items()

    # Check that the format on disk is as expected.
    rules_mk = os.path.join(paths.omd_root, "etc", "check_mk", "conf.d", "wato", "rules.mk")
    environ = load_mk_file(rules_mk, default={})
    stored_condition = environ[values["ruleset"]][0]["condition"]  # type: ignore[index]
    expected_condition = {
        "host_tags": {"criticality": "prod", "networking": {"$ne": "wan"}},
        "host_labels": {"os": "windows"},
    }
    assert stored_condition == expected_condition


def test_create_rule_with_string_value(rule_client: RulesTestClient) -> None:
    resp = rule_client.create(
        ruleset="extra_host_conf:notification_options",
        folder="/",
        properties={"description": "Test", "disabled": False},
        value_raw="'d,u,r,f,s'",
        conditions={},
    )
    assert resp.json["extensions"]["value_raw"] == "'d,u,r,f,s'"


def test_openapi_list_rules_with_hyphens(
    rule_client: RulesTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs.CheckTypeGroupSelection,
        "get_elements",
        lambda x: {"fileinfo_groups": "some title"},
    )
    STATIC_CHECKS_FILEINFO_GROUPS = "static_checks:fileinfo-groups"
    _, result = _create_rule(
        rule_client,
        "/",
        ruleset=STATIC_CHECKS_FILEINFO_GROUPS,
        value_raw="('fileinfo_groups', '', {'group_patterns': []})",
    )

    assert result["ruleset"] == STATIC_CHECKS_FILEINFO_GROUPS

    resp2 = rule_client.list_rules(ruleset=STATIC_CHECKS_FILEINFO_GROUPS)

    assert len(resp2.json["value"]) == 1
    assert resp2.json["value"][0]["extensions"]["ruleset"] == STATIC_CHECKS_FILEINFO_GROUPS


def test_openapi_list_rules(
    rule_client: RulesTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
) -> None:
    _, values = new_rule
    rule_set = values["ruleset"]
    resp = rule_client.list_rules(ruleset=rule_set)

    for entry in resp.json["value"]:
        assert entry["domainType"] == "rule"

    stored = resp.json["value"][0]["extensions"]
    assert stored["properties"]["disabled"] == values["properties"]["disabled"]
    assert stored["properties"]["comment"] == values["properties"]["comment"]
    # Do the complete round-trip check. Everything stored is also retrieved.
    assert stored["conditions"]["host_labels"] == values["conditions"]["host_labels"]
    assert stored["conditions"]["host_tags"] == values["conditions"]["host_tags"]


def test_openapi_delete_rule(
    api_client: RestApiClient,
    ruleset_client: RulesetTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
) -> None:
    resp, values = new_rule

    _resp = ruleset_client.get(ruleset_id=values["ruleset"])
    assert _resp.json["extensions"]["number_of_rules"] == 1

    api_client.follow_link(
        resp.json,
        ".../delete",
        headers={"If-Match": _resp.headers["ETag"]},
    ).assert_status_code(204)

    list_resp = ruleset_client.get(ruleset_id=values["ruleset"])
    assert list_resp.json["extensions"]["number_of_rules"] == 0

    api_client.follow_link(
        resp.json,
        ".../delete",
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.parametrize("ruleset", ["host_groups", "special_agents:gcp"])
def test_openapi_show_ruleset(ruleset_client: RulesetTestClient, ruleset: str) -> None:
    resp = ruleset_client.get(ruleset_id=urllib.parse.quote(ruleset))
    assert resp.json["extensions"]["name"] == ruleset


def test_openapi_show_non_existing_ruleset(
    ruleset_client: RulesetTestClient,
) -> None:
    # Request a ruleset that doesn't exist should return a 400 Bad Request.
    resp = ruleset_client.get(ruleset_id="non_existing_ruleset", expect_ok=False)
    resp.assert_status_code(404)


def test_openapi_list_rulesets(
    ruleset_client: RulesetTestClient,
) -> None:
    resp = ruleset_client.get_all(search_options="?fulltext=cisco_qos&used=False")
    assert len(resp.json["value"]) == 2


@pytest.mark.usefixtures("new_rule")
def test_openapi_has_rule(
    rule_client: RulesTestClient,
) -> None:
    assert _order_of_rules(rule_client) == ["They made me do it!"]


@pytest.mark.usefixtures("new_rule")
def test_openapi_create_rule_order(
    rule_client: RulesTestClient,
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    rule1, _ = _create_rule(rule_client, f"/{folder_name_one}", comment="rule1")
    rule1_id = rule1.json["id"]

    assert _order_of_rules(rule_client) == ["rule1", "They made me do it!"]

    rule2, _ = _create_rule(rule_client, f"/{folder_name_two}", comment="rule2")
    rule2_id = rule2.json["id"]

    assert _order_of_rules(rule_client) == ["rule2", "rule1", "They made me do it!"]

    rule_resp1 = rule_client.get(rule1_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_one}"

    rule_resp2 = rule_client.get(rule2_id)
    assert rule_resp2.json["extensions"]["folder"] == f"/{folder_name_two}"


def test_openapi_move_rule_to_top_of_folder(
    rule_client: RulesTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(rule_client, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(rule_client, f"/{folder_name_two}", comment="rule2")

    _move_to(rule_client, rule_id, "top_of_folder", folder=f"/{folder_name_one}")

    rule_resp1 = rule_client.get(rule_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_one}"

    assert _order_of_rules(rule_client) == ["rule2", "They made me do it!", "rule1"]


def test_openapi_move_rule_to_bottom_of_folder(
    rule_client: RulesTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(rule_client, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(rule_client, f"/{folder_name_two}", comment="rule2")

    _move_to(rule_client, rule_id, "bottom_of_folder", folder=f"/{folder_name_two}")

    rule_resp1 = rule_client.get(rule_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_two}"

    assert _order_of_rules(rule_client) == ["rule2", "They made me do it!", "rule1"]


def test_openapi_move_rule_after_specific_rule(
    rule_client: RulesTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    rule1, _ = _create_rule(rule_client, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(rule_client, f"/{folder_name_two}", comment="rule2")

    _move_to(rule_client, rule_id, "after_specific_rule", dest_rule_id=rule1.json["id"])

    rule_resp1 = rule_client.get(rule_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_one}"

    assert _order_of_rules(rule_client) == ["rule2", "rule1", "They made me do it!"]


def test_openapi_move_rule_before_specific_rule(
    rule_client: RulesTestClient,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(rule_client, f"/{folder_name_one}", comment="rule1")
    rule2, _ = _create_rule(rule_client, f"/{folder_name_two}", comment="rule2")

    _move_to(rule_client, rule_id, "before_specific_rule", dest_rule_id=rule2.json["id"])

    rule_resp = rule_client.get(rule_id)
    assert rule_resp.json["extensions"]["folder"] == f"/{folder_name_two}"

    assert _order_of_rules(rule_client) == ["They made me do it!", "rule2", "rule1"]


def test_create_rule_permission_error_regression(rule_client: RulesTestClient) -> None:
    rule_client.create(
        ruleset="active_checks:cmk_inv",
        folder="~",
        properties={"disabled": False},
        value_raw='{"status_data_inventory": True}',
        conditions={},
    )


def _move_to(
    rule_client: RulesTestClient,
    _rule_id: str,
    position: str,
    dest_rule_id: str | None = None,
    folder: str | None = None,
) -> Response:
    options: dict[str, Any] = {"position": position}
    if position in ("top_of_folder", "bottom_of_folder"):
        options["folder"] = folder
    elif position in ("before_specific_rule", "after_specific_rule"):
        options["rule_id"] = dest_rule_id

    _resp = rule_client.move(rule_id=_rule_id, options=options)

    if position in ("top_of_folder", "bottom_of_folder"):
        assert _resp.json["extensions"]["folder"] == folder

    return _resp


def _order_of_rules(rule_client: RulesTestClient) -> list[str]:
    _resp = rule_client.list_rules(ruleset="inventory_df_rules")
    comments = []
    for rule in _resp.json["value"]:
        comments.append(rule["extensions"]["properties"]["comment"])
    return comments


def test_user_needs_folder_permissions_to_move_rules(
    api_client: RestApiClient,
    rule_client: RulesTestClient,
    contactgroup_client: ContactGroupTestClient,
    with_user: tuple[UserId, str],
) -> None:
    source_folder = "source"
    dest_folder = "dest"

    api_client.create_folder(
        folder_name=source_folder,
        title=source_folder,
        parent="/",
        expect_ok=True,
    )
    api_client.create_folder(
        folder_name=dest_folder,
        title=dest_folder,
        parent="/",
        expect_ok=True,
    )

    # make_folder_inaccessible
    nobody = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    contactgroup_client.create(name=nobody, alias=nobody)
    api_client.edit_folder(
        folder_name=f"~{dest_folder}",
        title=nobody,
        attributes={"contactgroups": {"groups": [nobody]}},
    )

    resp = rule_client.create(
        ruleset="active_checks:cmk_inv",
        folder="~" + source_folder,
        properties={"disabled": False},
        value_raw='{"status_data_inventory": True}',
        conditions={},
    )

    rule_client.set_credentials(username=with_user[0], password=with_user[1])

    rule_client.move(
        rule_id=resp.json["id"],
        options={"position": "top_of_folder", "folder": "~" + dest_folder},
        expect_ok=False,
    ).assert_status_code(401)


def test_openapi_only_show_used_rulesets_by_default_regression(
    rule_client: RulesTestClient,
) -> None:
    """With default parameters, the 'list rulesets' endpoint should only show rulessets that are in use."""
    # make one ruleset used, so this tests won't pass on an empty result
    _create_rule(rule_client, "~")
    rulesets = rule_client.list_rulesets().json["value"]
    assert len(rulesets) > 0
    for ruleset in rulesets:
        assert ruleset["extensions"]["number_of_rules"] > 0


def test_openapi_fulltext_crash_regression(rule_client: RulesTestClient) -> None:
    """A fulltext search shouldn't crash the endpoint."""
    rule_client.list_rulesets(fulltext="cluster").assert_status_code(200)


def test_openapi_deprecated_filter_regression(rule_client: RulesTestClient) -> None:
    """No deprecated rules should be shown when they are filtered out."""

    # checkgroup_parameters:jvm_threads is deprecated.
    rule_client.create(
        ruleset="checkgroup_parameters:jvm_threads",
        value_raw="'(80, 100)'",
        conditions={"host_name": {"match_on": ["heute"], "operator": "one_of"}},
        properties={},
        expect_ok=False,
    )

    resp = rule_client.list_rulesets(deprecated=False)
    assert len(resp.json["value"]) == 0


def test_openapi_ruleset_search_invalid_regex_regression(ruleset_client: RulesetTestClient) -> None:
    """Searching for an invalid regex shouldn't crash"""
    ruleset_client.get_all("?fulltext=%5C&used=false", expect_ok=False).assert_status_code(400)
