#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import typing
import urllib
from collections.abc import Iterable
from typing import Any

import pytest

from cmk.ccc.site import omd_site
from cmk.ccc.store import load_mk_file, save_mk_file, save_to_mk_file
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.configuration_bundle_store import BundleId, ConfigBundleStore
from cmk.gui.watolib.configuration_bundles import create_config_bundle, CreateBundleEntities
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook
from cmk.utils import paths
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from cmk.utils.rulesets.definition import RuleGroup
from tests.testlib.rest_api_client import (
    ClientRegistry,
    Response,
    RestApiClient,
    RuleConditions,
    RuleProperties,
)

# Some core ruleset that is always registered, so this does not pull in the check_parameters
# plugins. It serialises as a plain ``periodic_discovery = [...]`` assignment, which the
# on-disk format check in test_openapi_create_rule relies on.
DEFAULT_RULESET = "periodic_discovery"
DEFAULT_VALUE_RAW = """{
    "severity_unmonitored": 1,
    "severity_changed_service_labels": 0,
    "severity_changed_service_params": 0,
    "severity_vanished": 0,
    "severity_new_host_label": 1,
    "check_interval": 120.0,
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
    ruleset: str = DEFAULT_RULESET,
    value_raw: str | None = DEFAULT_VALUE_RAW,
    conditions: RuleConditions | None = None,
    expect_ok: bool = True,
) -> tuple[Response, dict[str, Any]]:
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
    # Regression guard: a value_raw containing Python tuples must be accepted and parsed.
    value_raw = """{
        "name": "API2I",
        "host": {"address": ("direct", "mimi.ch"), "virthost": "mimi.ch"},
        "mode": ("url", {"uri": "/lala/misite.html", "ssl": "auto", "urlize": True}),
    }"""
    clients.Rule.create(
        ruleset=RuleGroup.ActiveChecks("http"),
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

    # Bundled rulesets like `discovery_parameters:<name>` / `checkgroup_parameters:<name>`
    # are stored as `<parent>['<name>'] = [...]` and therefore need an initial empty
    # dict for the parent variable in the exec context.
    parent, _, subkey = values["ruleset"].partition(":")
    default: dict[str, object] = {parent: {}} if subkey else {}
    environ = load_mk_file(rules_mk, default=default, lock=False)
    stored = environ[parent][subkey] if subkey else environ[parent]  # type: ignore[index]
    stored_condition = stored[0]["condition"]  # type: ignore[index]
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
    resp = clients.Rule.create(
        ruleset=ruleset,
        folder="/",
        properties={"description": "Test", "disabled": False},
        value_raw="{'summary': True}",
        conditions={},
        expect_ok=False,
    )
    resp.assert_status_code(400)


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
    api_client.follow_link(
        resp.json,
        ".../delete",
        headers={"If-Match": resp.headers["ETag"]},
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
    resp = clients.Ruleset.list(fulltext="notification_options", used=False)
    assert {r["id"] for r in resp.json["value"]} == {
        RuleGroup.ExtraHostConf("notification_options"),
        RuleGroup.ExtraServiceConf("notification_options"),
    }


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
    assert (
        resp.json["fields"]["body.conditions"]["msg"]
        == "Value error, Please provide the field 'host_labels' OR 'host_label_groups', not both."
    )


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
        user_permissions=UserPermissions({}, {}, {}, []),
        pprint_value=False,
        debug=False,
        pending_changes=PendingChanges(
            activation_sites=activation_sites(active_config.sites),
            local_site=omd_site(),
            acting_user=user.id,
            store=PendingChangesStore(),
            hooks=(
                make_audit_log_change_hook(use_git=False),
                sidebar_reload_change_hook,
                index_update_change_hook,
            ),
        ),
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


def test_openapi_edit_conditions(clients: ClientRegistry) -> None:
    # test that for rules that are not locked by Quick setup, the conditions can be edited
    resp = clients.Rule.create(
        ruleset="active_checks:http",
        folder="/",
        conditions=RuleConditions(
            host_name={
                "operator": "one_of",
                "match_on": ["example.com"],
            }
        ),
        value_raw='{"name": "check_localhost", "host": {"address": ("direct", "localhost")}, "mode": ("url", {})}',
    )

    clients.Rule.edit(
        rule_id=resp.json["id"],
        conditions=RuleConditions(
            host_name={
                "operator": "one_of",
                "match_on": ["example.com", "localhost"],
            }
        ),
        value_raw=resp.json["extensions"]["value_raw"],
    )


def _rule_order(clients: ClientRegistry, ruleset: str) -> list[str]:
    """Return rule IDs in their current folder order."""
    return [entry["id"] for entry in clients.Rule.list(ruleset).json["value"]]


def test_move_rule_to_top_of_folder(clients: ClientRegistry) -> None:
    rule_1 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_2 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_3 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]

    assert _rule_order(clients, DEFAULT_RULESET) == [rule_1, rule_2, rule_3]

    resp = clients.Rule.move(rule_3, {"position": "top_of_folder", "folder": "/"})
    assert resp.json["extensions"]["folder_index"] == 0
    assert _rule_order(clients, DEFAULT_RULESET) == [rule_3, rule_1, rule_2]


def test_move_rule_to_bottom_of_folder(clients: ClientRegistry) -> None:
    rule_1 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_2 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_3 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]

    assert _rule_order(clients, DEFAULT_RULESET) == [rule_1, rule_2, rule_3]

    resp = clients.Rule.move(rule_1, {"position": "bottom_of_folder", "folder": "/"})
    assert resp.json["extensions"]["folder_index"] == 2
    assert _rule_order(clients, DEFAULT_RULESET) == [rule_2, rule_3, rule_1]


def test_move_rule_before_specific_rule(clients: ClientRegistry) -> None:
    rule_1 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_2 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_3 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]

    assert _rule_order(clients, DEFAULT_RULESET) == [rule_1, rule_2, rule_3]

    resp = clients.Rule.move(rule_3, {"position": "before_specific_rule", "rule_id": rule_1})
    assert resp.json["extensions"]["folder_index"] == 0
    assert _rule_order(clients, DEFAULT_RULESET) == [rule_3, rule_1, rule_2]


def test_move_rule_after_specific_rule(clients: ClientRegistry) -> None:
    rule_1 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_2 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]
    rule_3 = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json[
        "id"
    ]

    assert _rule_order(clients, DEFAULT_RULESET) == [rule_1, rule_2, rule_3]

    resp = clients.Rule.move(rule_1, {"position": "after_specific_rule", "rule_id": rule_3})
    assert resp.json["extensions"]["folder_index"] == 2
    assert _rule_order(clients, DEFAULT_RULESET) == [rule_2, rule_3, rule_1]


def test_move_rule_to_different_folder(
    clients: ClientRegistry, test_folders: tuple[str, str]
) -> None:
    folder_1, folder_2 = test_folders
    rule = clients.Rule.create(
        DEFAULT_RULESET, folder=f"~{folder_1}", value_raw=DEFAULT_VALUE_RAW
    ).json["id"]

    resp = clients.Rule.move(rule, {"position": "top_of_folder", "folder": f"~{folder_2}"})
    assert resp.json["extensions"]["folder_index"] == 0
    assert folder_2 in resp.json["extensions"]["folder"]


def test_move_rule_to_top_of_folder_with_locked_rule(
    clients: ClientRegistry, locked_rule_id: str
) -> None:
    """top_of_folder places a regular rule after all Quick Setup rules, not at true index 0."""
    rule_1 = clients.Rule.create("host_label_rules", value_raw='{"foo": "bar"}').json["id"]
    rule_2 = clients.Rule.create("host_label_rules", value_raw='{"baz": "qux"}').json["id"]

    assert _rule_order(clients, "host_label_rules") == [locked_rule_id, rule_1, rule_2]

    resp = clients.Rule.move(rule_2, {"position": "top_of_folder", "folder": "/"})
    assert resp.json["extensions"]["folder_index"] == 1
    assert _rule_order(clients, "host_label_rules") == [locked_rule_id, rule_2, rule_1]


def test_move_rule_after_last_locked_rule(clients: ClientRegistry, locked_rule_id: str) -> None:
    """Moving after the only Quick Setup rule succeeds — it places the rule right after it."""
    rule_1 = clients.Rule.create("host_label_rules", value_raw='{"foo": "bar"}').json["id"]
    rule_2 = clients.Rule.create("host_label_rules", value_raw='{"baz": "qux"}').json["id"]

    assert _rule_order(clients, "host_label_rules") == [locked_rule_id, rule_1, rule_2]

    resp = clients.Rule.move(rule_2, {"position": "after_specific_rule", "rule_id": locked_rule_id})
    assert resp.json["extensions"]["folder_index"] == 1
    assert _rule_order(clients, "host_label_rules") == [locked_rule_id, rule_2, rule_1]


def test_move_rule_before_locked_rule(clients: ClientRegistry, locked_rule_id: str) -> None:
    """Moving before the only Quick Setup rule fails — it is not allowed."""
    rule_1 = clients.Rule.create("host_label_rules", value_raw='{"foo": "bar"}').json["id"]
    rule_2 = clients.Rule.create("host_label_rules", value_raw='{"baz": "qux"}').json["id"]

    assert _rule_order(clients, "host_label_rules") == [locked_rule_id, rule_1, rule_2]

    resp = clients.Rule.move(
        rule_2,
        {"position": "before_specific_rule", "rule_id": locked_rule_id},
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["detail"] == "Cannot move before a rule managed by Quick setup."


def test_move_rule_before_itself_fails(clients: ClientRegistry) -> None:
    rule = clients.Rule.create(DEFAULT_RULESET, folder="/", value_raw=DEFAULT_VALUE_RAW).json["id"]

    resp = clients.Rule.move(
        rule, {"position": "before_specific_rule", "rule_id": rule}, expect_ok=False
    ).assert_status_code(400)
    assert resp.json["detail"] == "You cannot move a rule before/after itself."
