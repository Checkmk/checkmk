#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# import json


import json

import pytest
from pytest_mock import MockerFixture

from tests.testlib.rest_api_client import ClientRegistry

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

import cmk.utils.version as cmk_version

mocked_phase_one_result = {
    "class_name": "Phase1Result",
    "attributes": {
        "connector_object": "PiggybackHosts",
        "attributes": {
            "hosts": ["some_host"],
            "tmpfs_initialization_time": 100000,
        },
        "status": {
            "class_name": "ExecutionStatus",
            "attributes": {"_steps": []},
            "_finished": True,
            "_time_initialized": 100000,
            "_time_completed": 100001,
        },
    },
}


@pytest.mark.skipif(
    cmk_version.edition() is cmk_version.Edition.CRE, reason="DCD not available in raw edition"
)
def test_dcd_fetch_phase_one_result(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mocker: MockerFixture,
) -> None:
    automation_patch = mocker.patch(
        "cmk.gui.watolib.automations.execute_phase1_result",
        return_value=mocked_phase_one_result,
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        "/NO_SITE/check_mk/api/1.0/domain-types/dcd/actions/fetch_phase_one/invoke",
        params=json.dumps(
            {
                "site_id": "NO_SITE",
                "connection_id": "connection_one",
            }
        ),
        headers={"Accept": "application/json"},
        content_type="application/json",
        status=200,
    )
    automation_patch.assert_called_once()
    assert resp.json["extensions"] == mocked_phase_one_result


def test_openapi_create_dcd(clients: ClientRegistry) -> None:
    clients.Dcd.create(
        dcd_id="dcd_10",
        title="My first auto DCD",
        site="NO_SITE",
        connector_type="piggyback",
    )


def test_openapi_get_dcd(clients: ClientRegistry) -> None:
    create_response = clients.Dcd.create(
        dcd_id="dcd_10", title="My first auto DCD", site="NO_SITE", connector_type="piggyback"
    )
    fetch_response = clients.Dcd.get("dcd_10")

    create_response_data = create_response.json["extensions"]
    fetch_response_data = fetch_response.json["extensions"]

    assert create_response_data["title"] == fetch_response_data["title"]
    assert create_response_data["site"] == fetch_response_data["site"]

    not_exists_response = clients.Dcd.get("dcd_11", expect_ok=False).assert_status_code(404)
    assert not_exists_response.json["title"] == "Not Found"


def test_openapi_create_dcd_fail(clients: ClientRegistry) -> None:
    # Missing required fields
    create_response_missing_title = clients.Dcd.create(
        dcd_id="dcd_09", site="NO_SITE", connector_type="piggyback", expect_ok=False
    )
    assert create_response_missing_title.status_code == 400

    # Already exists DCD
    clients.Dcd.create(
        dcd_id="dcd_10", title="My First auto DCD", site="NO_SITE", connector_type="piggyback"
    )
    duplicate_id_response = clients.Dcd.create(
        dcd_id="dcd_10",
        title="My second auto DCD",
        site="NO_SITE",
        connector_type="piggyback",
        expect_ok=False,
    )

    assert duplicate_id_response.status_code == 400
    assert duplicate_id_response.json["detail"] == "These fields have problems: dcd_id"
    assert len(duplicate_id_response.json["fields"]["dcd_id"]) == 1
    assert duplicate_id_response.json["fields"]["dcd_id"][0] == "ID 'dcd_10' already in use"

    # Folder not found
    folder_not_found_response = clients.Dcd.create(
        dcd_id="dcd_11",
        title="My second auto DCD",
        site="NO_SITE",
        connector_type="piggyback",
        creation_rules=[
            {
                "folder_path": "/folder/not/found",
                "delete_hosts": True,
                "host_attributes": {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "no-agent",
                },
            }
        ],
        expect_ok=False,
    )

    assert folder_not_found_response.status_code == 400
    assert folder_not_found_response.json["detail"] == "These fields have problems: creation_rules"
    assert len(folder_not_found_response.json["fields"]["creation_rules"]) == 1
    assert (
        folder_not_found_response.json["fields"]["creation_rules"]["0"]["folder_path"][0]
        == "The folder '/folder/not/found' could not be found."
    )

    # Invalid connector type
    bad_connector_type_response = clients.Dcd.create(
        dcd_id="dcd_10",
        title="My first auto DCD",
        site="NO_SITE",
        connector_type="i_do_not_exist",
        expect_ok=False,
    ).assert_status_code(400)
    print(bad_connector_type_response.json)
    assert (
        bad_connector_type_response.json["detail"] == "These fields have problems: connector_type"
    )
    assert len(bad_connector_type_response.json["fields"]["connector_type"]) == 1
    assert (
        bad_connector_type_response.json["fields"]["connector_type"][0]
        == "Unsupported value: i_do_not_exist"
    )


def test_openapi_create_dcd_default_values(clients: ClientRegistry) -> None:
    create_response = clients.Dcd.create(
        dcd_id="dcd_10", title="My First auto DCD", site="NO_SITE", connector_type="piggyback"
    )
    res = create_response.json["extensions"]

    assert res["title"] == "My First auto DCD"
    assert res["comment"] == ""
    assert res["docu_url"] == ""
    assert res["disabled"] is False
    assert res["site"] == "NO_SITE"

    name, connector = res["connector"]
    assert name == "piggyback"

    assert connector["interval"] == 60
    assert connector["discover_on_creation"]
    assert connector["no_deletion_time_after_init"] == 600
    assert connector["validity_period"] == 60

    assert len(connector["creation_rules"]) == 1
    creation_rules = connector["creation_rules"][0]
    assert creation_rules["create_folder_path"] == ""
    assert creation_rules["delete_hosts"] is False

    assert ["tag_snmp_ds", "no-snmp"] in creation_rules["host_attributes"]
    assert ["tag_agent", "no-agent"] in creation_rules["host_attributes"]
    assert ["tag_piggyback", "piggyback"] in creation_rules["host_attributes"]
    assert ["tag_address_family", "no-ip"] in creation_rules["host_attributes"]


def test_openapi_create_dcd_full_values(clients: ClientRegistry) -> None:
    clients.Folder.create(
        parent="/",
        folder_name="folder1",
        title="Group 1",
    )

    clients.Folder.create(
        parent="/folder1",
        folder_name="other_folder",
        title="Subgroup 1A",
    )

    # folder1/other_folder
    dcd = {
        "dcd_id": "dcd_11",
        "title": "My other auto DCD",
        "comment": "This is a comment explaining why I am here",
        "documentation_url": "https://example.com",
        "disabled": False,
        "site": "NO_SITE",
        "connector_type": "piggyback",
        "interval": 240,
        "discover_on_creation": True,
        "no_deletion_time_after_init": 1200,
        "validity_period": 120,
        "creation_rules": [
            {
                "folder_path": "/folder1/other_folder",
                "delete_hosts": True,
                "host_attributes": {
                    "tag_snmp_ds": "no-snmp",
                    "tag_agent": "no-agent",
                },
            }
        ],
        "exclude_time_ranges": [{"start": "12:00", "end": "14:00"}],
    }

    res = clients.Dcd.create(**dcd)  # type: ignore

    creation_response = res.json["extensions"]

    assert creation_response["title"] == dcd["title"]
    assert creation_response["comment"] == dcd["comment"]
    assert creation_response["docu_url"] == dcd["documentation_url"]
    assert creation_response["disabled"] == dcd["disabled"]
    assert creation_response["site"] == dcd["site"]

    name, connector = creation_response["connector"]
    assert name == "piggyback"

    assert connector["interval"] == dcd["interval"]
    assert connector["discover_on_creation"] == dcd["discover_on_creation"]
    assert connector["no_deletion_time_after_init"] == dcd["no_deletion_time_after_init"]
    assert connector["validity_period"] == dcd["validity_period"]

    assert len(connector["creation_rules"]) == 1
    creation_rules = connector["creation_rules"][0]
    assert creation_rules["create_folder_path"] == "folder1/other_folder"
    assert creation_rules["delete_hosts"]
    assert ["tag_snmp_ds", "no-snmp"] in creation_rules["host_attributes"]
    assert ["tag_agent", "no-agent"] in creation_rules["host_attributes"]

    assert len(connector["activation_exclude_times"]) == 1
    assert connector["activation_exclude_times"][0] == [["12", "00"], ["14", "00"]]


def test_openapi_delete_dcd(clients: ClientRegistry) -> None:
    clients.Dcd.create(
        dcd_id="dcd_A",
        title="First dynamic host configuration",
        site="NO_SITE",
        connector_type="piggyback",
    )

    clients.Dcd.get("dcd_A")

    clients.Dcd.delete("dcd_A").assert_status_code(204)

    retrieve_erased_dcd_response = clients.Dcd.get("dcd_A", expect_ok=False)
    assert retrieve_erased_dcd_response.status_code == 404
    assert retrieve_erased_dcd_response.json["title"] == "Not Found"
    assert retrieve_erased_dcd_response.json["detail"] == "These fields have problems: dcd_id"


def _count_pending_changes(clients: ClientRegistry) -> int:
    return len(clients.ActivateChanges.list_pending_changes().json["value"])


def test_openapi_activation_changes(clients: ClientRegistry) -> None:
    pending_changes_count = _count_pending_changes(clients)

    clients.Dcd.create(
        dcd_id="dcd_A",
        title="First dynamic host configuration",
        site="NO_SITE",
        connector_type="piggyback",
    )
    new_pending_changes_count = _count_pending_changes(clients)
    assert new_pending_changes_count == pending_changes_count + 1
    pending_changes_count = new_pending_changes_count

    clients.Dcd.get("dcd_A")
    new_pending_changes_count = _count_pending_changes(clients)
    assert new_pending_changes_count == pending_changes_count

    clients.Dcd.delete("dcd_A")
    new_pending_changes_count = _count_pending_changes(clients)
    assert new_pending_changes_count == pending_changes_count + 1
