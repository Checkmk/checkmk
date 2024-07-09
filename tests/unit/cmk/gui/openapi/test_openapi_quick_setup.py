#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Literal

import pytest

from tests.testlib.repo import repo_path
from tests.testlib.rest_api_client import ClientRegistry

from cmk.utils import paths

from cmk.ccc import version

cloud_only = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME,
    reason="Test data differs per edition",
)


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


def quick_setup_test_data() -> dict:
    with open(repo_path() / "tests/unit/cmk/gui/openapi/quick_setup_test_data.json") as f:
        return json.load(f)


def quick_setup_test_request_form_data(which_stage: Literal[1, 2, 3, 4]) -> dict:
    stage_1 = {
        "stage_id": 1,
        "form_data": {
            "aws_account_name": {
                "account_name": "nombre_de_cuenta_de_aws",
            },
            "credentials": {
                "access_key_id": "identificación_de_clave_de_acceso",
                "secret_access_key": {
                    "input_context": {
                        "legacy_varprefix_ca2f6299-622f-4339-80bb-14a4ae03bdda_sel": "0",
                        "legacy_varprefix_ca2f6299-622f-4339-80bb-14a4ae03bdda_0_orig": "",
                        "legacy_varprefix_ca2f6299-622f-4339-80bb-14a4ae03bdda_0": "",
                    },
                    "varprefix": "legacy_varprefix_ca2f6299-622f-4339-80bb-14a4ae03bdda",
                },
            },
        },
    }

    stage_2 = {
        "stage_id": 2,
        "form_data": {
            "host_data": {
                "host_name": "my_quick_setup_aws_host",
                "host_path": "a/path/to/my/quick_setup/aws/host",
            },
            "configure_host_and_region": {
                "regions_to_monitor": {
                    "input_context": {},
                },
            },
        },
    }
    stage_3 = {
        "stage_id": 3,
        "form_data": {
            "configure_services_to_monitor": {
                "global_services": {
                    "ce": [
                        "none",
                        {
                            "input_context": {},
                            "varprefix": "legacy_varprefix_0cf83b5e-df8b-4854-a17e-df05b79ff2cf",
                        },
                    ],
                    "route53": [
                        "none",
                        {
                            "input_context": {},
                            "varprefix": "legacy_varprefix_c9b7b71e-abb1-4227-be76-735a8492f849",
                        },
                    ],
                    "cloudfront": [
                        "none",
                        {
                            "input_context": {},
                            "varprefix": "legacy_varprefix_deb5987a-3307-4e4c-81c4-bdcb4d172aec",
                        },
                    ],
                },
                "services": {
                    "ec2": ["all", {"limits": "limits"}],
                    "ebs": ["all", {"limits": "limits"}],
                    "s3": ["all", {"limits": "limits"}],
                    "glacier": ["all", {"limits": "limits"}],
                    "elb": ["all", {"limits": "limits"}],
                    "elbv2": ["all", {"limits": "limits"}],
                    "rds": ["all", {"limits": "limits"}],
                    "cloudwatch_alarms": ["all", {"limits": "limits"}],
                    "dynamodb": ["all", {"limits": "limits"}],
                    "wafv2": ["all", {"limits": "limits"}],
                    "aws_lambda": ["all", {"limits": "limits"}],
                    "sns": ["all", {"limits": "limits"}],
                    "ecs": ["all", {"limits": "limits"}],
                    "elasticache": ["all", {"limits": "limits"}],
                },
            },
            "site": {"site_selection": {}},
            "aws_tags": {"overalltags": {}},
        },
    }
    stage_4 = {
        "stage_id": 4,
        "form_data": {},
    }
    if which_stage == 1:
        return stage_1
    if which_stage == 2:
        return {**stage_1, **stage_2}
    if which_stage == 3:
        return {**stage_1, **stage_2, **stage_3}
    return {**stage_1, **stage_2, **stage_3, **stage_4}


@pytest.mark.skip(reason="contains changing uuid in password field")
@pytest.mark.usefixtures("patch_theme")
def test_get_overview(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.get_overview("aws_quick_setup")
    resp_modified = remove_keys(obj=resp.json, keys_to_remove={"html", "varprefix", "input_hint"})
    assert resp_modified == {
        "quick_setup_id": "aws_quick_setup",
        "overviews": [
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
        ],
        "stage": {
            "stage_id": 1,
            "validation_errors": [],
            "stage_summary": [],
            "components": quick_setup_test_data()["stage_1"],
        },
    }


def test_get_overview_non_existing_quicksetup_id(clients: ClientRegistry) -> None:
    clients.QuickSetup.get_overview("frodo", expect_ok=False).assert_status_code(404)


@pytest.mark.usefixtures("patch_theme")
def test_send_aws_stage_one(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[quick_setup_test_request_form_data(1)],
    )
    resp_modified = remove_keys(obj=resp.json, keys_to_remove={"html", "varprefix", "input_hint"})
    assert resp_modified == {
        "stage_id": 2,
        "validation_errors": [],
        "stage_summary": [],
        "components": quick_setup_test_data()["stage_2"],
    }


@cloud_only
def test_send_aws_stage_two(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup", stages=[quick_setup_test_request_form_data(2)]
    )
    resp_modified = remove_keys(obj=resp.json, keys_to_remove={"html", "varprefix", "input_hint"})
    assert resp_modified == {
        "stage_id": 3,
        "validation_errors": [],
        "stage_summary": [],
        "components": quick_setup_test_data()["stage_3"],
    }


@cloud_only
def test_send_aws_stage_three(clients: ClientRegistry) -> None:
    _resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[quick_setup_test_request_form_data(3)],
        expect_ok=False,
    )
    # assert resp.json == {
    #     "stage_id": 4,
    #     "validation_errors": [],
    #     "stage_summary": [],
    #     "components": [],
    # }


@cloud_only
def test_send_aws_stage_four(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.send_stage_retrieve_next(
        quick_setup_id="aws_quick_setup",
        stages=[quick_setup_test_request_form_data(4)],
    )
    assert resp.json == {
        "stage_id": -1,
        "validation_errors": [],
        "stage_summary": [],
        "components": [],
    }


def test_quick_setup_save(clients: ClientRegistry) -> None:
    resp = clients.QuickSetup.complete_quick_setup(
        quick_setup_id="aws_quick_setup",
        payload={"stages": []},
    )
    resp.assert_status_code(201)
    assert resp.json == {"redirect_url": "http://save/url"}
