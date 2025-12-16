#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry, RestApiException
from tests.unit.cmk.web_test_app import SetConfig

# mypy: disable-error-code="unreachable"

# also remove the mypy disable when re enabling the tests
pytest.skip("Needs to be rewritten with CMK-28417", allow_module_level=True)


def test_list_rule_form_specs(clients: ClientRegistry) -> None:
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.rule_form_spec,
        entity_type_specifier="special_agents:elasticsearch",
    )

    assert resp.status_code == 200, resp.json
    assert {entry["title"] for entry in resp.json["value"]} == {"Elasticsearch"}
    assert {entry["id"] for entry in resp.json["value"]} == {"special_agents:elasticsearch"}


def test_list_rule_form_specs_without_perm(set_config: SetConfig, clients: ClientRegistry) -> None:
    with set_config():
        clients.User.create(
            username="guest_user1",
            fullname="guest_user1_alias",
            auth_option={"auth_type": "password", "password": "supersecretish"},
            roles=["guest"],
        )
        clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

        with pytest.raises(RestApiException) as excinfo:
            clients.ConfigurationEntity.list_configuration_entities(
                entity_type=ConfigEntityType.rule_form_spec,
                entity_type_specifier="special_agents:elasticsearch",
            )

        assert excinfo.value.response.status_code == 401
        assert excinfo.value.response.json == {
            "title": "Unauthorized",
            "status": 401,
            "detail": (
                "We are sorry, but you lack the permission for this operation."
                " If you do not like this then please ask your administrator"
                " to provide you with the following permission: '<b>Rulesets</b>'."
            ),
        }


def test_get_rule_form_spec_without_perm(set_config: SetConfig, clients: ClientRegistry) -> None:
    with set_config():
        clients.User.create(
            username="guest_user1",
            fullname="guest_user1_alias",
            auth_option={"auth_type": "password", "password": "supersecretish"},
            roles=["guest"],
        )
        clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

        with pytest.raises(RestApiException) as excinfo:
            clients.ConfigurationEntity.get_configuration_entity_schema(
                entity_type=ConfigEntityType.rule_form_spec,
                entity_type_specifier="special_agents:elasticsearch",
            )

        assert excinfo.value.response.status_code == 401
        assert excinfo.value.response.json == {
            "title": "Unauthorized",
            "status": 401,
            "detail": (
                "We are sorry, but you lack the permission for this operation."
                " If you do not like this then please ask your administrator"
                " to provide you with the following permission: '<b>Rulesets</b>'."
            ),
        }


def test_create_rule_form_spec(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "labels",
        [
            {"name": "foo", "value": "bar"},
        ],
    )
    mock_livestatus.add_table(
        "status",
        [
            {
                "livestatus_version": "2.5.0",
                "program_version": "Check_MK 2.5.0",
                "program_start": 0,
                "num_hosts": 0,
                "num_services": 0,
                "max_long_output_size": 0,
                "core_pid": 0,
                "edition": "edition",
            },
        ],
    )

    with mock_livestatus():
        mock_livestatus.expect_query("GET labels\nColumns: name value\n")
        schema_resp = clients.ConfigurationEntity.get_configuration_entity_schema(
            entity_type=ConfigEntityType.rule_form_spec,
            entity_type_specifier="special_agents:elasticsearch",
        )

    rule_id = schema_resp.json["extensions"]["schema"]["elements"][0]["elements"][4][
        "parameter_form"
    ]["value"]

    protocol = schema_resp.json["extensions"]["schema"]["elements"][1]["elements"][0][
        "parameter_form"
    ]["elements"][3]["default_value"]

    folder_path = schema_resp.json["extensions"]["schema"]["elements"][2]["elements"][0][
        "parameter_form"
    ]["elements"][0]["default_value"]["folder_path"]

    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.rule_form_spec.value,
            "entity_type_specifier": "special_agents:elasticsearch",
            "data": {
                "properties": {
                    "description": "",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "id": rule_id,
                    "_name": "special_agents:elasticsearch",
                },
                "value": {
                    "value": {
                        "hosts": ["my_host"],
                        "protocol": protocol,
                        "port": 9200,
                        "cluster_health": False,
                        "nodes": False,
                    }
                },
                "conditions": {"type": ["explicit", {"folder_path": folder_path}]},
            },
        }
    )

    assert resp.status_code == 200, resp.json
    assert resp.json["title"] == "Elasticsearch"
    assert resp.json["id"] == "special_agents:elasticsearch"


def test_create_rule_form_spec_without_perm(
    mock_livestatus: MockLiveStatusConnection, set_config: SetConfig, clients: ClientRegistry
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "labels",
        [
            {"name": "foo", "value": "bar"},
        ],
    )
    mock_livestatus.add_table(
        "status",
        [
            {
                "livestatus_version": "2.5.0",
                "program_version": "Check_MK 2.5.0",
                "program_start": 0,
                "num_hosts": 0,
                "num_services": 0,
                "max_long_output_size": 0,
                "core_pid": 0,
                "edition": "edition",
            },
        ],
    )

    with mock_livestatus():
        mock_livestatus.expect_query("GET labels\nColumns: name value\n")
        schema_resp = clients.ConfigurationEntity.get_configuration_entity_schema(
            entity_type=ConfigEntityType.rule_form_spec,
            entity_type_specifier="special_agents:elasticsearch",
        )

    rule_id = schema_resp.json["extensions"]["schema"]["elements"][0]["elements"][4][
        "parameter_form"
    ]["value"]

    protocol = schema_resp.json["extensions"]["schema"]["elements"][1]["elements"][0][
        "parameter_form"
    ]["elements"][3]["default_value"]

    folder_path = schema_resp.json["extensions"]["schema"]["elements"][2]["elements"][0][
        "parameter_form"
    ]["elements"][0]["default_value"]["folder_path"]

    with set_config():
        clients.User.create(
            username="guest_user1",
            fullname="guest_user1_alias",
            auth_option={"auth_type": "password", "password": "supersecretish"},
            roles=["guest"],
        )
        clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

        with pytest.raises(RestApiException) as excinfo:
            clients.ConfigurationEntity.create_configuration_entity(
                {
                    "entity_type": ConfigEntityType.rule_form_spec.value,
                    "entity_type_specifier": "special_agents:elasticsearch",
                    "data": {
                        "properties": {
                            "description": "",
                            "comment": "",
                            "docu_url": "",
                            "disabled": False,
                            "id": rule_id,
                            "_name": "special_agents:elasticsearch",
                        },
                        "value": {
                            "value": {
                                "hosts": ["my_host"],
                                "protocol": protocol,
                                "port": 9200,
                                "cluster_health": False,
                                "nodes": False,
                            }
                        },
                        "conditions": {"type": ["explicit", {"folder_path": folder_path}]},
                    },
                }
            )

        assert excinfo.value.response.status_code == 401
        assert excinfo.value.response.json == {
            "title": "Unauthorized",
            "status": 401,
            "detail": (
                "We are sorry, but you lack the permission for this operation."
                " If you do not like this then please ask your administrator"
                " to provide you with the following permission: '<b>Rulesets</b>'."
            ),
        }


def test_create_rule_form_spec_cannot_overwrite_existing(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "labels",
        [
            {"name": "foo", "value": "bar"},
        ],
    )
    mock_livestatus.add_table(
        "status",
        [
            {
                "livestatus_version": "2.5.0",
                "program_version": "Check_MK 2.5.0",
                "program_start": 0,
                "num_hosts": 0,
                "num_services": 0,
                "max_long_output_size": 0,
                "core_pid": 0,
                "edition": "edition",
            },
        ],
    )

    with mock_livestatus():
        mock_livestatus.expect_query("GET labels\nColumns: name value\n")
        schema_resp = clients.ConfigurationEntity.get_configuration_entity_schema(
            entity_type=ConfigEntityType.rule_form_spec,
            entity_type_specifier="special_agents:elasticsearch",
        )

    rule_id = schema_resp.json["extensions"]["schema"]["elements"][0]["elements"][4][
        "parameter_form"
    ]["value"]

    protocol = schema_resp.json["extensions"]["schema"]["elements"][1]["elements"][0][
        "parameter_form"
    ]["elements"][3]["default_value"]

    folder_path = schema_resp.json["extensions"]["schema"]["elements"][2]["elements"][0][
        "parameter_form"
    ]["elements"][0]["default_value"]["folder_path"]

    clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.rule_form_spec.value,
            "entity_type_specifier": "special_agents:elasticsearch",
            "data": {
                "properties": {
                    "description": "",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "id": rule_id,
                    "_name": "special_agents:elasticsearch",
                },
                "value": {
                    "value": {
                        "hosts": ["my_host_1"],
                        "protocol": protocol,
                        "port": 9200,
                        "cluster_health": False,
                        "nodes": False,
                    }
                },
                "conditions": {"type": ["explicit", {"folder_path": folder_path}]},
            },
        }
    )

    with pytest.raises(RestApiException) as excinfo:
        clients.ConfigurationEntity.create_configuration_entity(
            {
                "entity_type": ConfigEntityType.rule_form_spec.value,
                "entity_type_specifier": "special_agents:elasticsearch",
                "data": {
                    "properties": {
                        "description": "",
                        "comment": "",
                        "docu_url": "",
                        "disabled": False,
                        "id": rule_id,
                        "_name": "special_agents:elasticsearch",
                    },
                    "value": {
                        "value": {
                            "hosts": ["my_host_2"],
                            "protocol": protocol,
                            "port": 9200,
                            "cluster_health": False,
                            "nodes": False,
                        }
                    },
                    "conditions": {"type": ["explicit", {"folder_path": folder_path}]},
                },
            }
        )

    assert excinfo.value.response.status_code == 409
    assert excinfo.value.response.json["title"] == "Rule ID conflict"
    assert excinfo.value.response.json["detail"].startswith("Cannot overwrite the existing rule")


def test_create_rule_form_spec_twice(
    mock_livestatus: MockLiveStatusConnection, clients: ClientRegistry
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "labels",
        [
            {"name": "foo", "value": "bar"},
        ],
    )
    mock_livestatus.add_table(
        "status",
        [
            {
                "livestatus_version": "2.5.0",
                "program_version": "Check_MK 2.5.0",
                "program_start": 0,
                "num_hosts": 0,
                "num_services": 0,
                "max_long_output_size": 0,
                "core_pid": 0,
                "edition": "edition",
            },
        ],
    )

    with mock_livestatus():
        mock_livestatus.expect_query("GET labels\nColumns: name value\n")
        schema_resp_1 = clients.ConfigurationEntity.get_configuration_entity_schema(
            entity_type=ConfigEntityType.rule_form_spec,
            entity_type_specifier="special_agents:elasticsearch",
        )

    rule_id_1 = schema_resp_1.json["extensions"]["schema"]["elements"][0]["elements"][4][
        "parameter_form"
    ]["value"]

    protocol_1 = schema_resp_1.json["extensions"]["schema"]["elements"][1]["elements"][0][
        "parameter_form"
    ]["elements"][3]["default_value"]

    folder_path_1 = schema_resp_1.json["extensions"]["schema"]["elements"][2]["elements"][0][
        "parameter_form"
    ]["elements"][0]["default_value"]["folder_path"]

    clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.rule_form_spec.value,
            "entity_type_specifier": "special_agents:elasticsearch",
            "data": {
                "properties": {
                    "description": "",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "id": rule_id_1,
                    "_name": "special_agents:elasticsearch",
                },
                "value": {
                    "value": {
                        "hosts": ["my_host"],
                        "protocol": protocol_1,
                        "port": 9200,
                        "cluster_health": False,
                        "nodes": False,
                    }
                },
                "conditions": {"type": ["explicit", {"folder_path": folder_path_1}]},
            },
        }
    )
    assert clients.Ruleset.list().json["value"][0]["extensions"]["number_of_rules"] == 1

    with mock_livestatus():
        mock_livestatus.expect_query("GET labels\nColumns: name value\n")
        schema_resp_2 = clients.ConfigurationEntity.get_configuration_entity_schema(
            entity_type=ConfigEntityType.rule_form_spec,
            entity_type_specifier="special_agents:elasticsearch",
        )

    rule_id_2 = schema_resp_2.json["extensions"]["schema"]["elements"][0]["elements"][4][
        "parameter_form"
    ]["value"]

    protocol_2 = schema_resp_2.json["extensions"]["schema"]["elements"][1]["elements"][0][
        "parameter_form"
    ]["elements"][3]["default_value"]

    folder_path_2 = schema_resp_2.json["extensions"]["schema"]["elements"][2]["elements"][0][
        "parameter_form"
    ]["elements"][0]["default_value"]["folder_path"]

    clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.rule_form_spec.value,
            "entity_type_specifier": "special_agents:elasticsearch",
            "data": {
                "properties": {
                    "description": "",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "id": rule_id_2,
                    "_name": "special_agents:elasticsearch",
                },
                "value": {
                    "value": {
                        "hosts": ["my_host"],
                        "protocol": protocol_2,
                        "port": 9200,
                        "cluster_health": False,
                        "nodes": False,
                    }
                },
                "conditions": {"type": ["explicit", {"folder_path": folder_path_2}]},
            },
        }
    )
    assert clients.Ruleset.list().json["value"][0]["extensions"]["number_of_rules"] == 2


def test_update_rule_form_spec_not_implemented(clients: ClientRegistry) -> None:
    resp = clients.ConfigurationEntity.update_configuration_entity(
        {
            "entity_type": ConfigEntityType.rule_form_spec.value,
            "entity_type_specifier": "special_agents:elasticsearch",
            "entity_id": "123",
            "data": {},
        },
        expect_ok=False,
    )
    resp.assert_rest_api_crash()
