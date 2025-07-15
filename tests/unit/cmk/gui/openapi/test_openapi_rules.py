#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing
import urllib
from collections.abc import Iterable, Mapping
from typing import Any

import pytest

from tests.testlib.unit.rest_api_client import (
    ClientRegistry,
    Response,
    RestApiClient,
    RuleConditions,
    RuleProperties,
)

from cmk.ccc.store import load_mk_file, save_mk_file, save_to_mk_file

from cmk.utils import paths
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.logged_in import user
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundleStore
from cmk.gui.watolib.configuration_bundles import create_config_bundle, CreateBundleEntities

DEFAULT_VALUE_RAW = """{
    "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
    "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
}"""

DEFAULT_CONDITIONS: RuleConditions = {
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
    "host_label_groups": [
        {
            "operator": "and",
            "label_group": [
                {
                    "operator": "and",
                    "label": "os:windows",
                }
            ],
        },
    ],
}


@pytest.fixture(scope="function", name="new_rule")
def new_rule_fixture(clients: ClientRegistry) -> tuple[Response, dict[str, Any]]:
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
    value: dict[str, Any] | list[Any] | tuple | str | None = None,
    value_raw: str | None = DEFAULT_VALUE_RAW,
    conditions: RuleConditions | None = None,
    expect_ok: bool = True,
) -> tuple[Response, dict[str, Any]]:
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

    if conditions is None:
        conditions = DEFAULT_CONDITIONS

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
        expect_ok=expect_ok,
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
        ruleset=RuleGroup.CheckgroupParameters("filesystem"),
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False, "description": "API2I"},
    )


def test_openapi_value_raw_is_unaltered(clients: ClientRegistry) -> None:
    value_raw = "{'levels': ('fixed', (10.0, 5.0))}"
    resp = clients.Rule.create(
        ruleset=RuleGroup.CheckgroupParameters("memory_percentage_used"),
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
        "host": {"address": ("direct", "mimi.ch"), "virthost": "mimi.ch"},
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
        ruleset=RuleGroup.ActiveChecks("http"),
        value_raw=value_raw,
        conditions={},
        folder="~",
        properties={"disabled": False},
    )
    clients.Rule.get(rule_id=resp.json["id"])


def test_openapi_rules_href_escaped(clients: ClientRegistry) -> None:
    resp = clients.Ruleset.list(used=False)
    ruleset = next(r for r in resp.json["value"] if RuleGroup.SpecialAgents("gcp") == r["id"])
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
    # assert "You have not defined any host group yet" in resp.json["detail"]


def test_openapi_create_rule(
    clients: ClientRegistry,
    new_rule: tuple[Response, dict[str, typing.Any]],
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
    rules_mk = paths.omd_root / "etc/check_mk/conf.d/wato/rules.mk"
    environ = load_mk_file(rules_mk, default={}, lock=False)
    stored_condition = environ[values["ruleset"]][0]["condition"]  # type: ignore[index]
    expected_condition = {
        "host_tags": {"criticality": "prod", "networking": {"$ne": "wan"}},
        "host_label_groups": [("and", [("and", "os:windows")])],
    }
    assert stored_condition == expected_condition


def test_create_rule_with_string_value(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
        ruleset=RuleGroup.ExtraHostConf("notification_options"),
        folder="/",
        properties={"description": "Test", "disabled": False},
        value_raw="'d,u,r,f,s'",
        conditions={},
    )
    assert resp.json["extensions"]["value_raw"] == "'d,u,r,f,s'"


def test_create_rule_stores_migrated_value(clients: ClientRegistry) -> None:
    ruleset = "diskstat_inventory"
    clients.Rule.create(
        ruleset=ruleset,
        folder="/",
        properties={"description": "Test", "disabled": False},
        value_raw="{'summary': True }",
        conditions={},
    )
    rules_path = paths.omd_root / "etc/check_mk/conf.d/wato/rules.mk"
    rules: Mapping[str, Any] = load_mk_file(rules_path, default={}, lock=False)
    assert rules[ruleset][0]["value"] == {
        "summary": True,
        "lvm": False,
        "vxvm": False,
        "diskless": False,
    }


def test_openapi_list_rules(
    clients: ClientRegistry,
    new_rule: tuple[Response, dict[str, typing.Any]],
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
    assert stored["conditions"]["host_label_groups"] == values["conditions"]["host_label_groups"]
    assert stored["conditions"]["host_tags"] == values["conditions"]["host_tags"]


def test_openapi_delete_rule(
    api_client: RestApiClient,
    clients: ClientRegistry,
    new_rule: tuple[Response, dict[str, typing.Any]],
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


@pytest.mark.parametrize("ruleset", ["host_groups", RuleGroup.SpecialAgents("gcp")])
def test_openapi_show_ruleset(clients: ClientRegistry, ruleset: str) -> None:
    resp = clients.Ruleset.get(ruleset_id=urllib.parse.quote(ruleset))
    assert resp.json["extensions"]["name"] == ruleset


def test_openapi_show_non_existing_ruleset(clients: ClientRegistry) -> None:
    # Request a ruleset that doesn't exist should return a 400 Bad Request.
    resp = clients.Ruleset.get(ruleset_id="non_existing_ruleset", expect_ok=False)
    resp.assert_status_code(404)


def test_openapi_list_rulesets(clients: ClientRegistry) -> None:
    resp = clients.Ruleset.list(fulltext="cisco_qos", used=False)
    assert len(resp.json["value"]) == 2


def test_create_rule_old_label_format(
    clients: ClientRegistry,
    new_rule: tuple[Response, dict[str, typing.Any]],
) -> None:
    """This test can be removed when the old "host_labels" field is eventually removed."""

    # Create rule - new format
    _, values = new_rule

    # add field "host_labels" with the old format & remove the new field "host_label_groups"
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

    clients.Rule.create(
        ruleset=values["ruleset"],
        folder=values["folder"],
        properties=values["properties"],
        value_raw=values["value_raw"],
        conditions=conditions,
    )


def test_create_rule_old_and_new_label_formats(
    clients: ClientRegistry,
    new_rule: tuple[Response, dict[str, typing.Any]],
) -> None:
    """This test can be removed when the old "host_labels" field is eventually removed."""
    # Create rule - new format
    _, values = new_rule

    # add field "host_labels" - Sending old format + new format
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
        "host_label_groups": [
            {"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]}
        ],
    }

    resp = clients.Rule.create(
        ruleset=values["ruleset"],
        folder=values["folder"],
        properties=values["properties"],
        value_raw=values["value_raw"],
        conditions=conditions,
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"]["conditions"]["_schema"] == [
        "Please provide the field 'host_labels' OR 'host_label_groups', not both."
    ]


def test_create_rule_missing_operator(clients: ClientRegistry) -> None:
    conditions: RuleConditions = {"service_description": {"operator": "one_of"}}
    resp, _ = _create_rule(
        clients=clients,
        folder="/",
        comment="They made me do it!",
        description="This is my title for this very important rule.",
        documentation_url="http://example.com/",
        conditions=conditions,
        expect_ok=False,
    )
    resp.assert_status_code(400)


def test_create_rule_missing_match_on(clients: ClientRegistry) -> None:
    conditions: RuleConditions = {"service_description": {"match_on": []}}
    resp, _ = _create_rule(
        clients=clients,
        folder="/",
        comment="They made me do it!",
        description="This is my title for this very important rule.",
        documentation_url="http://example.com/",
        conditions=conditions,
        expect_ok=False,
    )
    resp.assert_status_code(400)


def test_create_rule_empty_match_on_str(clients: ClientRegistry) -> None:
    conditions: RuleConditions = {
        "host_name": {
            "operator": "one_of",
            "match_on": [""],
        }
    }
    resp, _ = _create_rule(
        clients=clients,
        folder="/",
        comment="They made me do it!",
        description="This is my title for this very important rule.",
        documentation_url="http://example.com/",
        conditions=conditions,
        expect_ok=False,
    )
    resp.assert_status_code(400)


def test_create_rule_no_conditions_nor_properties(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
        ruleset="active_checks:http",
        folder="/",
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )

    clients.Rule.get(rule_id=resp.json["id"])


def test_create_rule_no_conditions(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
        ruleset="active_checks:http",
        folder="/",
        properties={},
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )

    clients.Rule.get(rule_id=resp.json["id"])


def test_create_rule_no_properties(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
        ruleset="active_checks:http",
        folder="/",
        conditions={},
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )

    clients.Rule.get(rule_id=resp.json["id"])


def test_openapi_create_rule_reject_incompatible_value_raw(clients: ClientRegistry) -> None:
    clients.Rule.create(
        ruleset="checkgroup_parameters:memory_linux",
        folder="/",
        conditions={},
        value_raw='{"memory": {"horizon": 90, "levels_upper": ("absolute", (0.5, 1.0)), "period": "24x7"}}',
        expect_ok=False,
    )


def test_openapi_edit_rule_reject_incompatible_value_raw(clients: ClientRegistry) -> None:
    resp = clients.Rule.create(
        ruleset="active_checks:http",
        folder="/",
        conditions={},
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )

    clients.Rule.edit(
        rule_id=resp.json["id"],
        value_raw='{"memory": {"horizon": 90, "levels_upper": ("absolute", (0.5, 1.0)), "period": "24x7"}}',
        expect_ok=False,
    ).assert_rest_api_crash()


def test_openapi_create_rule_label_groups_no_operator(clients: ClientRegistry) -> None:
    clients.Rule.create(
        ruleset="active_checks:http",
        folder="/",
        conditions={
            "host_label_groups": [{"label_group": [{"operator": "and", "label": "os:windows"}]}]
        },
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )


@pytest.fixture(name="locked_rule_id")
def fixture_locked_rule_id() -> Iterable[str]:
    bundle_id = BundleId("bundle_id")
    program_id = PROGRAM_ID_QUICK_SETUP
    create_config_bundle(
        bundle_id=bundle_id,
        bundle={
            "title": "bundle_title",
            "comment": "bundle_comment",
            "owned_by": "user_id",
            "group": "bundle_group",
            "program_id": program_id,
        },
        entities=CreateBundleEntities(),
        user_id=user.id,
        pprint_value=False,
        use_git=False,
        debug=False,
    )

    rules_mk = paths.omd_root / "etc/check_mk/conf.d/wato/rules.mk"
    content: str | None = None
    if rules_mk.exists():
        with open(rules_mk) as f:
            content = f.read()
    id_ = "f893cdfc-00c8-4d93-943b-05c4edc52068"
    save_to_mk_file(
        rules_mk,
        key="host_label_rules",
        value=[
            {
                "id": id_,
                "value": {"custom": "label"},
                "condition": {"host_name": ["heute"]},
                "options": {"disabled": False},
                "locked_by": {
                    "site_id": "heute",
                    "program_id": program_id,
                    "instance_id": bundle_id,
                },
            },
        ],
    )
    yield id_

    # remove Quick setup config bundle
    store = ConfigBundleStore()
    all_bundles = store.load_for_modification()
    all_bundles.pop(bundle_id)
    store.save(all_bundles, pprint_value=False)

    if content is None:
        rules_mk.unlink()
    else:
        save_mk_file(rules_mk, content)


def test_openapi_cannot_delete_locked_rule(clients: ClientRegistry, locked_rule_id: str) -> None:
    resp = clients.Rule.delete(locked_rule_id, expect_ok=False).assert_status_code(400)
    assert resp.json["detail"] == "Rules managed by Quick setup cannot be deleted."


def test_openapi_cannot_move_locked_rule(clients: ClientRegistry, locked_rule_id: str) -> None:
    resp = clients.Rule.move(
        locked_rule_id, {"position": "top_of_folder", "folder": "/"}, expect_ok=False
    ).assert_status_code(400)
    assert resp.json["detail"] == "Rules managed by Quick setup cannot be moved."


def test_openapi_cannot_move_rule_before_locked_rule(
    clients: ClientRegistry, locked_rule_id: str
) -> None:
    clients.Ruleset.list()
    rule_resp = clients.Rule.create("host_label_rules", value_raw='{"foo": "bar"}')
    move_resp = clients.Rule.move(
        rule_resp.json["id"],
        {"position": "before_specific_rule", "rule_id": locked_rule_id},
        expect_ok=False,
    ).assert_status_code(400)
    assert move_resp.json["detail"] == "Cannot move before a rule managed by Quick setup."


def test_openapi_cannot_change_locked_rule_conditions(
    clients: ClientRegistry, locked_rule_id: str
) -> None:
    get_resp = clients.Rule.get(locked_rule_id)
    resp = clients.Rule.edit(
        locked_rule_id,
        value_raw=get_resp.json["extensions"]["value_raw"],
        conditions=DEFAULT_CONDITIONS,
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["detail"] == "Conditions cannot be modified for rules managed by Quick setup."
