#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

import pytest

from tests.testlib.rest_api_client import ClientRegistry


# TODO Once all the formspecs are implemented, this can be removed and the correct data can be added
def remove_keys(obj: Any, keys_to_remove: set[str]) -> Any:
    if isinstance(obj, dict):
        return {
            key: remove_keys(value, keys_to_remove)
            for key, value in obj.items()
            if key not in keys_to_remove
        }

    if isinstance(obj, list):
        return [remove_keys(item, keys_to_remove) for item in obj]

    return obj


def verify_stage_1_components(components: list[dict]) -> None:
    components = remove_keys(components, {"html", "varprefix"})
    assert components == [
        {
            "widget_type": "list",
            "items": [
                "Go to AWS root account > Services > IAM.",
                "Click 'Add user' under Users, select 'Access key - Programmatic access', and attach the 'ReadOnlyAccess' policy*.",
                "Save the generated access key and secret key for later use.",
            ],
            "ordered": False,
        },
        {
            "app_name": "form_spec",
            "data": {
                "account_name": "",
            },
            "id": "aws_account_name",
            "spec": {
                "elements": [
                    {
                        "default_value": "",
                        "ident": "account_name",
                        "parameter_form": {
                            "help": "",
                            "placeholder": None,
                            "title": "AWS account name",
                            "type": "string",
                            "validators": [
                                {
                                    "error_message": "The minimum allowed length is 1.",
                                    "max_value": None,
                                    "min_value": 1,
                                    "type": "length_in_range",
                                },
                            ],
                        },
                        "required": True,
                    },
                ],
                "help": "",
                "title": "",
                "type": "dictionary",
                "validators": [],
            },
            "validation": [],
        },
        {
            "widget_type": "note_text",
            "text": "*Since this is a ReadOnlyAccess, we will never create any resources on your AWS account",
        },
        {
            "id": "credentials",
            "app_name": "form_spec",
            "spec": {
                "type": "dictionary",
                "title": "",
                "help": "",
                "validators": [],
                "elements": [
                    {
                        "ident": "access_key_id",
                        "required": True,
                        "default_value": "",
                        "parameter_form": {
                            "type": "string",
                            "title": "The access key ID for your AWS account",
                            "help": "",
                            "validators": [
                                {
                                    "type": "length_in_range",
                                    "min_value": 1,
                                    "max_value": None,
                                    "error_message": "The minimum allowed length is 1.",
                                }
                            ],
                            "placeholder": None,
                        },
                    },
                    {
                        "ident": "secret_access_key",
                        "required": True,
                        "default_value": {},
                        "parameter_form": {
                            "type": "legacy_valuespec",
                            "title": "The secret access key for your AWS account",
                            "help": "",
                            "validators": [],
                        },
                    },
                ],
            },
            "data": {"access_key_id": "", "secret_access_key": {}},
            "validation": [],
        },
    ]


def verify_stage_2_components(components: list[dict]) -> None:
    components = remove_keys(components, {"html", "varprefix"})

    assert components == [
        {
            "id": "configure_host_and_region",
            "app_name": "form_spec",
            "spec": {
                "type": "dictionary",
                "title": "",
                "help": "",
                "validators": [],
                "elements": [
                    {
                        "ident": "regions_to_monitor",
                        "required": True,
                        "default_value": {},
                        "parameter_form": {
                            "type": "legacy_valuespec",
                            "title": "Regions to monitor",
                            "help": "",
                            "validators": [],
                        },
                    }
                ],
            },
            "data": {"regions_to_monitor": {}},
            "validation": [],
        }
    ]


@pytest.mark.usefixtures("patch_theme")
def test_get_overview(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.get_overview("aws_quick_setup")
    assert resp.json["quick_setup_id"] == "aws_quick_setup"
    assert resp.json["overviews"] == [
        {
            "stage_id": 1,
            "title": "Prepare AWS for Checkmk",
            "sub_title": None,
        },
        {
            "stage_id": 2,
            "title": "Configure host and regions",
            "sub_title": "Name your host, define the path and select the regions you would like to monitor",
        },
        {
            "stage_id": 3,
            "title": "Configure services to monitor",
            "sub_title": "Select and configure AWS services you would like to monitor",
        },
        {
            "stage_id": 4,
            "title": "Review and run service discovery",
            "sub_title": "Review your configuration, run and preview service discovery",
        },
    ]

    assert resp.json["stage"]["stage_id"] == 1
    assert resp.json["stage"]["validation_errors"] == []
    assert resp.json["stage"]["stage_summary"] == []
    verify_stage_1_components(components=resp.json["stage"]["components"])


def test_get_overview_non_existing_quicksetup_id(clients: ClientRegistry) -> None:
    clients.QuickSetup.get_overview("frodo", expect_ok=False).assert_status_code(404)


@pytest.mark.usefixtures("patch_theme")
def test_send_aws_stage_one(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[
            {
                "stage_id": 1,
                "form_data": {
                    "aws_account_name": {
                        "account_name": "nombre_de_cuenta_de_aws",
                    },
                    "credentials": {
                        "access_key_id": "identificación_de_clave_de_acceso",
                        "secret_access_key": {
                            "input_context": {
                                "explicit": "clave de acceso secreta",
                            },
                        },
                    },
                },
            }
        ],
    )
    assert resp.json["stage_id"] == 2
    assert resp.json["validation_errors"] == []
    assert resp.json["stage_summary"] == []
    verify_stage_2_components(components=resp.json["components"])


def test_send_aws_stage_two(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[
            {
                "stage_id": 1,
                "form_data": {
                    "aws_account_name": {
                        "account_name": "nombre_de_cuenta_de_aws",
                    },
                    "credentials": {
                        "access_key_id": "identificación_de_clave_de_acceso",
                        "secret_access_key": {
                            "input_context": {},
                        },
                    },
                },
            },
            {
                "stage_id": 2,
                "form_data": {
                    "configure_host_and_region": {
                        "regions_to_monitor": {
                            "input_context": {},
                        },
                    },
                },
            },
        ],
    )
    assert resp.json == {
        "stage_id": 3,
        "components": [],
        "validation_errors": [],
        "stage_summary": [],
    }


def test_send_aws_stage_three(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[
            {"stage_id": 1, "form_data": {}},
            {"stage_id": 2, "form_data": {}},
            {"stage_id": 3, "form_data": {}},
        ],
    )
    assert resp.json == {
        "stage_id": 4,
        "validation_errors": [],
        "stage_summary": [],
        "components": [],
    }


def test_send_aws_stage_four(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[
            {"stage_id": 1, "form_data": {}},
            {"stage_id": 2, "form_data": {}},
            {"stage_id": 3, "form_data": {}},
            {"stage_id": 4, "form_data": {}},
        ],
    )
    assert resp.json == {
        "stage_id": -1,
        "validation_errors": [],
        "stage_summary": [],
        "components": [],
    }
