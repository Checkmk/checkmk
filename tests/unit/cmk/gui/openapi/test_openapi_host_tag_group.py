#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Literal

import pytest

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.tags import BuiltinTagConfig
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.web_test_app import WebTestAppForCMK


@pytest.mark.usefixtures(
    "suppress_remote_automation_calls", "suppress_spec_generation_in_background"
)
def test_openapi_host_tag_group_update(
    clients: ClientRegistry,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    clients.HostTagGroup.create(
        ident="invalid%$",
        title="foobar",
        tags=[{"id": "pod", "title": "Pod"}],
        expect_ok=False,
    ).assert_status_code(400)

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "foo",
                "title": "foobar",
                "topic": "nothing",
                "tags": [
                    {
                        "id": "tester",
                        "title": "something",
                    }
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_tag_group/foo",
        params=json.dumps(
            {
                "tags": [
                    {
                        "id": "tutu",
                        "title": "something",
                    }
                ]
            }
        ),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/foo",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json["extensions"] == {
        "tags": [{"id": "tutu", "title": "something", "aux_tags": []}],
        "topic": "nothing",
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_get_collection(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    builtin_groups_count = len(BuiltinTagConfig().tag_groups)

    col_resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(col_resp.json_body["value"]) == builtin_groups_count


@pytest.mark.usefixtures(
    "suppress_remote_automation_calls",
    "suppress_spec_generation_in_background",
)
def test_openapi_host_tag_group_delete(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "foo",
                "title": "foobar",
                "topic": "nothing",
                "tags": [
                    {
                        "id": "tester",
                        "title": "something",
                    }
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/host_tag_group/foo",
        params=json.dumps({}),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=204,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/foo",
        headers={"Accept": "application/json"},
        status=404,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_host_tag_group_invalid_id(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "1",
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"id": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=400,
        content_type="application/json",
    )


@pytest.mark.usefixtures(
    "suppress_remote_automation_calls", "suppress_spec_generation_in_background"
)
def test_openapi_host_tag_group_built_in(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    built_in_tags = [tag_group.title for tag_group in BuiltinTagConfig().tag_groups]
    assert all(
        title in (entry["title"] for entry in resp.json_body["value"]) for title in built_in_tags
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/agent",
        headers={"Accept": "application/json"},
        status=200,
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_tag_group/agent",
        params=json.dumps(
            {
                "tags": [
                    {
                        "id": "tutu",
                        "title": "something",
                    }
                ]
            }
        ),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=405,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/host_tag_group/agent",
        params=json.dumps({}),
        headers={"Accept": "application/json"},
        status=405,
        content_type="application/json",
    )


@pytest.mark.usefixtures(
    "suppress_remote_automation_calls", "suppress_spec_generation_in_background"
)
def test_openapi_host_tag_group_update_use_case(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "group_id999",
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"id": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/host_tag_group/group_id999",
        params=json.dumps(
            {
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"id": "pod", "title": "Pod"}],
            }
        ),
        headers={"If-Match": resp.headers["ETag"], "Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _ = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/group_id999",
        headers={"Accept": "application/json"},
        status=200,
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_host_tag_with_only_one_option(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    clients: ClientRegistry,
    with_host: list[str],
) -> None:
    base = "/NO_SITE/check_mk/api/1.0"
    wsgi_app = aut_user_auth_wsgi_app
    wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "group_id999",
                "title": "Kubernetes",
                "topic": "Data Sources",
                "help": "Kubernetes Pods",
                "tags": [{"id": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    host = clients.HostConfig.get("example.com")
    clients.HostConfig.edit(
        host_name="example.com", attributes={"alias": "foobar", "tag_group_id999": "pod"}
    )
    host = clients.HostConfig.get(host_name="example.com")

    assert host.json["extensions"]["attributes"]["alias"] == "foobar"
    assert host.json["extensions"]["attributes"]["tag_group_id999"] == "pod"

    res = clients.HostConfig.edit(
        host_name="example.com",
        attributes={"tag_group_id999": "poddy"},  # non-existing choice
        expect_ok=False,
    )

    res.assert_status_code(400)
    assert res.json["detail"].startswith("These fields have problems")
    assert res.json["fields"]["attributes"][0].startswith("Invalid value for tag-group")

    clients.HostConfig.edit(
        host_name="example.com", attributes={"alias": "foobar", "tag_group_id999": None}
    )
    host = clients.HostConfig.get("example.com")
    assert host.json["extensions"]["attributes"]["tag_group_id999"] is None


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_host_tag_groups_all_props_in_schema(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> None:
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    first_tag = resp.json["value"][0]
    assert "title" in first_tag
    assert "id" in first_tag
    assert "topic" in first_tag["extensions"]
    assert "tags" in first_tag["extensions"]


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_host_tags_groups_without_topic_and_tags(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base: str
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_tag_group/collections/all",
        params=json.dumps(
            {
                "id": "group_id999",
                "title": "Kubernetes",
                "help": "Kubernetes Pods",
                "tags": [{"id": "pod", "title": "Pod"}],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    individual_resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/host_tag_group/group_id999",
        headers={"Accept": "application/json"},
        status=200,
    )

    assert individual_resp.json["extensions"]["topic"] == "Tags"

    # Let's see if outward validation works here as well
    aut_user_auth_wsgi_app.get(
        base + "/domain-types/host_tag_group/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_host_tag_group_empty_tags(clients: ClientRegistry) -> None:
    clients.HostTagGroup.create(
        ident="group_id999",
        title="Kubernetes",
        help_text="Kubernetes Pods",
        tags=[],
        expect_ok=False,
    )

    clients.HostTagGroup.create(
        ident="group_id999",
        title="Kubernetes",
        help_text="Kubernetes Pods",
        tags=[{"id": "pod", "title": "Pod"}],
    )

    clients.HostTagGroup.edit(
        ident="group_id999",
        tags=[],
        expect_ok=False,
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
@pytest.mark.parametrize(
    "delete_options",
    [
        pytest.param({}, id="default"),
        pytest.param({"repair": False}, id="explicit-no-repair"),
        pytest.param({"mode": "abort"}, id="abort-mode"),
    ],
)
def test_openapi_delete_dependant_host_tag(
    clients: ClientRegistry,
    delete_options: dict[str, Any],
) -> None:
    clients.HostTagGroup.create(
        ident="group_id999",
        title="Kubernetes",
        help_text="Kubernetes Pods",
        tags=[{"id": "pod", "title": "Pod"}],
    )
    clients.HostConfig.create(
        host_name="example.com",
        attributes={"tag_group_id999": "pod"},
    )
    resp = clients.HostTagGroup.delete(
        ident="group_id999",
        expect_ok=False,
        **delete_options,
    ).assert_status_code(401)

    assert resp.json["detail"].startswith(
        "The host tag group you intend to delete is used in the following occurrences: hosts (example.com)."
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
@pytest.mark.parametrize("mode", ["delete", "remove"])
def test_openapi_delete_host_tag_mode(
    clients: ClientRegistry,
    mode: Literal["delete", "remove"],
) -> None:
    clients.HostTagGroup.create(
        ident="group_id999",
        title="Kubernetes",
        help_text="Kubernetes Pods",
        tags=[{"id": "pod", "title": "Pod"}],
    )
    clients.HostConfig.create(
        host_name="example.com",
        attributes={"tag_group_id999": "pod"},
    )
    rule_resp = clients.Rule.create(
        ruleset=RuleGroup.CheckgroupParameters("memory_percentage_used"),
        value_raw="{'levels': (10.0, 5.0)}",
        conditions={
            "host_tags": [
                {
                    "key": "group_id999",
                    "operator": "is",
                    "value": "pod",
                },
            ]
        },
    )

    clients.HostTagGroup.delete(
        ident="group_id999",
        mode=mode,
    )

    resp = clients.HostConfig.get("example.com")
    assert "tag_group_id999" not in resp.json["extensions"]["attributes"]

    if mode == "delete":
        clients.Rule.get(rule_id=rule_resp.json["id"], expect_ok=False).assert_status_code(404)

    else:  # mode == "remove"
        resp = clients.Rule.get(rule_id=rule_resp.json["id"])
        assert len(resp.json["extensions"]["conditions"]["host_tags"]) == 0


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_delete_host_tag_repair_and_mode_not_compatible(
    clients: ClientRegistry,
) -> None:
    clients.HostTagGroup.create(
        ident="group_id999",
        title="Kubernetes",
        help_text="Kubernetes Pods",
        tags=[{"id": "pod", "title": "Pod"}],
    )
    resp = clients.HostTagGroup.delete(
        ident="group_id999",
        repair=True,
        mode="delete",
        expect_ok=False,
    ).assert_status_code(400)

    assert resp.json["detail"].startswith("Cannot use both repair and mode")


invalid_tag_group_ids = (
    "test_tag_group_id\n",
    "test_tag_group_id$%",
    "test_tag_group_id\\n",
    "test_tag_gr\noup_id",
    "\ntest_tag_group_id",
)


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
@pytest.mark.parametrize("group_id", invalid_tag_group_ids)
def test_host_tag_group_ident_with_newline(
    clients: ClientRegistry,
    group_id: str,
) -> None:
    resp = clients.HostTagGroup.create(
        ident=group_id,
        title="not_important",
        help_text="not_important",
        tags=[{"id": "pod", "title": "Pod"}],
        expect_ok=False,
    )

    resp.assert_status_code(400)
    assert resp.json["fields"]["id"][0].startswith(f"Invalid tag ID: {group_id!r}")


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_host_tag_group_creation_when_aux_tag_exists(
    clients: ClientRegistry,
) -> None:
    tag_id = "test123"

    aux_tag_data = {
        "aux_tag_id": tag_id,
        "title": "test",
        "topic": "test",
    }
    clients.AuxTag.create(tag_data=aux_tag_data)

    clients.HostTagGroup.create(
        ident=tag_id,
        title="test",
        tags=[{"id": "test", "title": "test"}],
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_openapi_identifiation_field(clients: ClientRegistry) -> None:
    clients.HostTagGroup.create(
        ident="test_group",
        title="Test group",
        help_text="My test groupd",
        tags=[{"id": "test", "title": "Test Tag"}],
    )

    res = clients.HostTagGroup.get(ident="test_group")
    assert "id" in res.json
    assert "id" in res.json["extensions"]["tags"][0]


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_id_already_in_use_by_custom_tag_group(clients: ClientRegistry) -> None:
    custom_tag_group = "criticality"
    clients.HostTagGroup.create(
        ident=custom_tag_group,
        title="tag_group_1",
        tags=[
            {"id": "prod", "title": "Production"},
            {"id": "test", "title": "Testing site"},
            {"id": "beta", "title": "Beta site"},
        ],
    )

    custom_tag_group_resp = clients.HostTagGroup.create(
        ident=custom_tag_group,
        title="tag_group_2",
        tags=[
            {"id": "prod", "title": "Production"},
            {"id": "test", "title": "Testing site"},
            {"id": "beta", "title": "Beta site"},
        ],
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The specified tag group id is already in use: '{custom_tag_group}'"
        in custom_tag_group_resp.json["fields"]["id"]
    )


def test_id_already_in_use_by_builtin_tag_group(clients: ClientRegistry) -> None:
    builtin_tag_group = "agent"

    builtin_tag_group_resp = clients.HostTagGroup.create(
        ident=builtin_tag_group,
        title="tag_group_3",
        tags=[
            {"id": "prod", "title": "Production"},
            {"id": "test", "title": "Testing site"},
            {"id": "beta", "title": "Beta site"},
        ],
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The specified tag group id is already in use: '{builtin_tag_group}'"
        in builtin_tag_group_resp.json["fields"]["id"]
    )


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_id_already_in_use_by_custom_aux_tag(clients: ClientRegistry) -> None:
    custom_aux_tag = "interface"

    clients.AuxTag.create(
        tag_data={
            "aux_tag_id": custom_aux_tag,
            "title": "aux_tag_1",
            "topic": "topic_1",
        },
    )

    custom_aux_tag_resp = clients.HostTagGroup.create(
        ident=custom_aux_tag,
        title="tag_group_2",
        tags=[
            {"id": "prod", "title": "Production"},
            {"id": "test", "title": "Testing site"},
            {"id": "beta", "title": "Beta site"},
        ],
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The specified tag group id is already in use: '{custom_aux_tag}'"
        in custom_aux_tag_resp.json["fields"]["id"]
    )


def test_id_in_use_by_builtin_aux_tag(clients: ClientRegistry) -> None:
    builtin_aux_tag = "snmp"

    builtin_aux_tag_resp = clients.HostTagGroup.create(
        ident=builtin_aux_tag,
        title="tag_group_4",
        tags=[
            {"id": "prod", "title": "Production"},
            {"id": "test", "title": "Testing site"},
            {"id": "beta", "title": "Beta site"},
        ],
        expect_ok=False,
    ).assert_status_code(400)

    assert (
        f"The specified tag group id is already in use: '{builtin_aux_tag}'"
        in builtin_aux_tag_resp.json["fields"]["id"]
    )
