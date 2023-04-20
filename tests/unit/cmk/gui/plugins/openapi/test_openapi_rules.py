#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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
    ClientRegistry,
    Response,
    RestApiClient,
    RuleConditions,
    RuleProperties,
)

from cmk.utils import paths
from cmk.utils.store import load_mk_file
from cmk.utils.type_defs import UserId

import cmk.gui.watolib.check_mk_automations
import cmk.gui.watolib.rulespecs


@pytest.fixture(scope="function", name="new_rule")
def new_rule_fixture(clients: ClientRegistry) -> tuple[TestResponse, dict[str, Any]]:
    return _create_rule(
        clients,
        folder="/",
        comment="They made me do it!",
        description="This is my title for this very important rule.",
        documentation_url="http://example.com/",
    )


def _create_rule(
    clients: ClientRegistry,
    folder: str,
    comment: str = "",
    description: str = "",
    documentation_url: str = "",
    disabled: bool = False,
    ruleset: str = "inventory_df_rules",
    value_raw: str = """{
        "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
        "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
    }""",
) -> tuple[TestResponse, dict[str, Any]]:
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

    resp = clients.Rule.create(
        ruleset=ruleset,
        folder=folder,
        properties=properties,
        value_raw=value_raw,
        conditions=conditions,
    )
    return resp, values


@pytest.fixture(scope="function", name="test_folders")
def site_with_test_folders(clients: ClientRegistry) -> tuple[str, str]:
    test_folder_name_one = "test_folder_1"
    test_folder_name_two = "test_folder_2"

    clients.Folder.create(
        folder_name=test_folder_name_one,
        title=test_folder_name_one,
        parent="/",
        expect_ok=True,
    )
    clients.Folder.create(
        folder_name=test_folder_name_two,
        title=test_folder_name_two,
        parent="/",
        expect_ok=True,
    )

    return test_folder_name_one, test_folder_name_two


def test_openapi_get_non_existing_rule(clients: ClientRegistry) -> None:
    clients.Rule.get(rule_id="non_existing_rule_id", expect_ok=False).assert_status_code(404)


def test_openapi_create_rule_regression(clients: ClientRegistry) -> None:
    value_raw = '{"inodes_levels": (10.0, 5.0), "levels": [(0, (0, 0)), (0, (0.0, 0.0))], "magic": 0.8, "trend_perfdata": True}'
    clients.Rule.create(
        ruleset="checkgroup_parameters:filesystem",
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False, "description": "API2I"},
    )


def test_openapi_value_raw_is_unaltered(clients: ClientRegistry) -> None:
    value_raw = "{'levels': (10.0, 5.0)}"
    resp = clients.Rule.create(
        ruleset="checkgroup_parameters:memory_percentage_used",
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False},
    )
    resp2 = clients.Rule.get(rule_id=resp.json["id"])
    assert value_raw == resp2.json["extensions"]["value_raw"]


def test_openapi_value_active_check_http(clients: ClientRegistry) -> None:
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
    resp = clients.Rule.create(
        ruleset="active_checks:http",
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False},
    )

    clients.Rule.get(rule_id=resp.json["id"])


def test_openapi_rules_href_escaped(clients: ClientRegistry) -> None:
    resp = clients.Ruleset.list(search_options="?used=0")
    ruleset = next(r for r in resp.json["value"] if "special_agents:gcp" == r["id"])
    assert (
        ruleset["links"][0]["href"]
        == "http://localhost/NO_SITE/check_mk/api/1.0/objects/ruleset/special_agents%253Agcp"
    )


def test_openapi_create_rule_failure(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
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
    assert "You have not defined any host group yet" in resp.json["detail"]


def test_openapi_create_rule(
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
) -> None:
    new_resp, values = new_rule

    resp = clients.Ruleset.get(ruleset_id=values["ruleset"])
    assert resp.json["extensions"]["number_of_rules"] == 1

    # Also fetch the newly created rule and check if it's actually persisted.
    resp2 = clients.Rule.get(new_resp.json["id"])
    ext = resp2.json["extensions"]
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


def test_create_rule_with_string_value(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
        ruleset="extra_host_conf:notification_options",
        folder="/",
        properties={"description": "Test", "disabled": False},
        value_raw="'d,u,r,f,s'",
        conditions={},
    )
    assert resp.json["extensions"]["value_raw"] == "'d,u,r,f,s'"


def test_openapi_list_rules_with_hyphens(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs.CheckTypeGroupSelection,
        "get_elements",
        lambda x: {"fileinfo_groups": "some title"},
    )
    STATIC_CHECKS_FILEINFO_GROUPS = "static_checks:fileinfo-groups"
    _, result = _create_rule(
        clients,
        "/",
        ruleset=STATIC_CHECKS_FILEINFO_GROUPS,
        value_raw="('fileinfo_groups', '', {'group_patterns': []})",
    )

    assert result["ruleset"] == STATIC_CHECKS_FILEINFO_GROUPS

    resp2 = clients.Rule.list(ruleset=STATIC_CHECKS_FILEINFO_GROUPS)

    assert len(resp2.json["value"]) == 1
    assert resp2.json["value"][0]["extensions"]["ruleset"] == STATIC_CHECKS_FILEINFO_GROUPS


def test_openapi_list_rules(
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
) -> None:

    _, values = new_rule
    rule_set = values["ruleset"]
    resp = clients.Rule.list(ruleset=rule_set)

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
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
) -> None:
    resp, values = new_rule

    _resp = clients.Ruleset.get(ruleset_id=values["ruleset"])
    assert _resp.json["extensions"]["number_of_rules"] == 1

    api_client.follow_link(
        resp.json,
        ".../delete",
        headers={"If-Match": _resp.headers["ETag"]},
    ).assert_status_code(204)

    list_resp = clients.Ruleset.get(ruleset_id=values["ruleset"])
    assert list_resp.json["extensions"]["number_of_rules"] == 0

    api_client.follow_link(
        resp.json,
        ".../delete",
        expect_ok=False,
    ).assert_status_code(404)


@pytest.mark.parametrize("ruleset", ["host_groups", "special_agents:gcp"])
def test_openapi_show_ruleset(clients: ClientRegistry, ruleset: str) -> None:
    resp = clients.Ruleset.get(ruleset_id=urllib.parse.quote(ruleset))
    assert resp.json["extensions"]["name"] == ruleset


def test_openapi_show_non_existing_ruleset(clients: ClientRegistry) -> None:
    resp = clients.Ruleset.get(ruleset_id="non_existing_ruleset", expect_ok=False)
    resp.assert_status_code(404)


def test_openapi_list_rulesets(clients: ClientRegistry) -> None:
    resp = clients.Ruleset.list(search_options="?fulltext=cisco_qos&used=False")
    assert len(resp.json["value"]) == 2


@pytest.mark.usefixtures("new_rule")
def test_openapi_has_rule(clients: ClientRegistry) -> None:
    assert _order_of_rules(clients) == ["They made me do it!"]


@pytest.mark.usefixtures("new_rule")
def test_openapi_create_rule_order(
    clients: ClientRegistry,
    test_folders: tuple[str, str],
) -> None:

    folder_name_one, folder_name_two = test_folders
    rule1, _ = _create_rule(clients, f"/{folder_name_one}", comment="rule1")
    rule1_id = rule1.json["id"]

    assert _order_of_rules(clients) == ["rule1", "They made me do it!"]

    rule2, _ = _create_rule(clients, f"/{folder_name_two}", comment="rule2")
    rule2_id = rule2.json["id"]

    assert _order_of_rules(clients) == ["rule2", "rule1", "They made me do it!"]

    rule_resp1 = clients.Rule.get(rule1_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_one}"

    rule_resp2 = clients.Rule.get(rule2_id)
    assert rule_resp2.json["extensions"]["folder"] == f"/{folder_name_two}"


def test_openapi_move_rule_to_top_of_folder(
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(clients, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(clients, f"/{folder_name_two}", comment="rule2")

    _move_to(clients, rule_id, "top_of_folder", folder=f"/{folder_name_one}")

    rule_resp1 = clients.Rule.get(rule_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_one}"

    assert _order_of_rules(clients) == ["rule2", "They made me do it!", "rule1"]


def test_openapi_move_rule_to_bottom_of_folder(
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(clients, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(clients, f"/{folder_name_two}", comment="rule2")

    _move_to(clients, rule_id, "bottom_of_folder", folder=f"/{folder_name_two}")

    rule_resp1 = clients.Rule.get(rule_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_two}"

    assert _order_of_rules(clients) == ["rule2", "They made me do it!", "rule1"]


def test_openapi_move_rule_after_specific_rule(
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    rule1, _ = _create_rule(clients, f"/{folder_name_one}", comment="rule1")
    _rule2, _ = _create_rule(clients, f"/{folder_name_two}", comment="rule2")

    _move_to(clients, rule_id, "after_specific_rule", dest_rule_id=rule1.json["id"])

    rule_resp1 = clients.Rule.get(rule_id)
    assert rule_resp1.json["extensions"]["folder"] == f"/{folder_name_one}"

    assert _order_of_rules(clients) == ["rule2", "rule1", "They made me do it!"]


def test_openapi_move_rule_before_specific_rule(
    clients: ClientRegistry,
    new_rule: tuple[TestResponse, dict[str, typing.Any]],
    test_folders: tuple[str, str],
) -> None:
    folder_name_one, folder_name_two = test_folders
    resp, _ = new_rule
    rule_id = resp.json["id"]

    _rule1, _ = _create_rule(clients, f"/{folder_name_one}", comment="rule1")
    rule2, _ = _create_rule(clients, f"/{folder_name_two}", comment="rule2")

    _move_to(clients, rule_id, "before_specific_rule", dest_rule_id=rule2.json["id"])

    rule_resp = clients.Rule.get(rule_id)
    assert rule_resp.json["extensions"]["folder"] == f"/{folder_name_two}"

    assert _order_of_rules(clients) == ["They made me do it!", "rule2", "rule1"]


def test_create_rule_permission_error_regression(clients: ClientRegistry) -> None:
    clients.Rule.create(
        ruleset="active_checks:cmk_inv",
        folder="~",
        properties={"disabled": False},
        value_raw='{"status_data_inventory": True}',
        conditions={},
    )


def _move_to(
    clients: ClientRegistry,
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

    _resp = clients.Rule.move(rule_id=_rule_id, options=options)

    if position in ("top_of_folder", "bottom_of_folder"):
        assert _resp.json["extensions"]["folder"] == folder

    return _resp


def _order_of_rules(clients: ClientRegistry) -> list[str]:
    _resp = clients.Rule.list(ruleset="inventory_df_rules")
    comments = []
    for rule in _resp.json["value"]:
        comments.append(rule["extensions"]["properties"]["comment"])
    return comments


def test_user_needs_folder_permissions_to_move_rules(
    clients: ClientRegistry,
    with_user: tuple[UserId, str],
) -> None:
    source_folder = "source"
    dest_folder = "dest"

    clients.Folder.create(
        folder_name=source_folder,
        title=source_folder,
        parent="/",
        expect_ok=True,
    )
    clients.Folder.create(
        folder_name=dest_folder,
        title=dest_folder,
        parent="/",
        expect_ok=True,
    )

    # make_folder_inaccessible
    nobody = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    clients.ContactGroup.create(name=nobody, alias=nobody)
    clients.Folder.edit(
        folder_name=f"~{dest_folder}",
        title=nobody,
        attributes={"contactgroups": {"groups": [nobody]}},
    )

    resp = clients.Rule.create(
        ruleset="active_checks:cmk_inv",
        folder="~" + source_folder,
        properties={"disabled": False},
        value_raw='{"status_data_inventory": True}',
        conditions={},
    )

    clients.Rule.set_credentials(username=with_user[0], password=with_user[1])

    clients.Rule.move(
        rule_id=resp.json["id"],
        options={"position": "top_of_folder", "folder": "~" + dest_folder},
        expect_ok=False,
    ).assert_status_code(401)


def test_openapi_only_show_used_rulesets_by_default_regression(
    clients: ClientRegistry,
) -> None:
    """With default parameters, the 'list rulesets' endpoint should only show rulessets that are in use."""
    # make one ruleset used, so this tests won't pass on an empty result
    _create_rule(clients, "~")
    rulesets = clients.Ruleset.list().json["value"]
    assert len(rulesets) > 0
    for ruleset in rulesets:
        assert ruleset["extensions"]["number_of_rules"] > 0


def test_openapi_fulltext_crash_regression(clients: ClientRegistry) -> None:
    """A fulltext search shouldn't crash the endpoint."""
    clients.Ruleset.list(fulltext="cluster").assert_status_code(200)


def test_openapi_deprecated_filter_regression(clients: ClientRegistry) -> None:
    """No deprecated rules should be shown when they are filtered out."""

    # checkgroup_parameters:jvm_threads is deprecated.
    clients.Rule.create(
        ruleset="checkgroup_parameters:jvm_threads",
        value_raw="'(80, 100)'",
        conditions={"host_name": {"match_on": ["heute"], "operator": "one_of"}},
        properties={},
        expect_ok=False,
    )

    resp = clients.Ruleset.list(deprecated=False)
    assert len(resp.json["value"]) == 0


def test_openapi_ruleset_search_invalid_regex_regression(clients: ClientRegistry) -> None:
    """Searching for an invalid regex shouldn't crash"""
    clients.Ruleset.list(
        search_options="?fulltext=%5C&used=false",
        expect_ok=False,
    ).assert_status_code(400)


def test_openapi_cannot_move_rules_from_different_rulesets_regression(
    clients: ClientRegistry,
) -> None:
    resp = clients.Rule.create(
        "custom_checks",
        value_raw=repr(
            {
                "service_description": "Test-Service",
                "command_line": 'echo "123"',
            }
        ),
        conditions={},
    )
    lhs_rule_id = resp.json["id"]

    resp = clients.Rule.create("active_checks:tcp", value_raw=repr((1, {})), conditions={})
    rhs_rule_id = resp.json["id"]

    clients.Rule.move(
        lhs_rule_id, {"after_specific_rule": rhs_rule_id}, expect_ok=False
    ).assert_status_code(400)

    clients.Rule.move(
        lhs_rule_id, {"before_specific_rule": rhs_rule_id}, expect_ok=False
    ).assert_status_code(400)


def test_openapi_cannot_move_rule_before_or_after_itself(clients: ClientRegistry) -> None:
    resp = clients.Rule.create("active_checks:tcp", value_raw=repr((1, {})), conditions={})
    rule_id = resp.json["id"]

    clients.Rule.move(
        rule_id, {"after_specific_rule": rule_id}, expect_ok=False
    ).assert_status_code(400)

    clients.Rule.move(
        rule_id, {"before_specific_rule": rule_id}, expect_ok=False
    ).assert_status_code(400)
