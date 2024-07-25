#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.quick_setup.definitions import ParsedFormData
from cmk.utils.quick_setup.widgets import FormSpecId

from cmk.base.server_side_calls import load_special_agents

from cmk.gui.quick_setup.to_frontend import (
    _collect_params_from_form_data,
    _collect_passwords_from_form_data,
)

ALL_FORM_SPEC_DATA: ParsedFormData = {
    FormSpecId("formspec_unique_id"): {
        "account_name": "my_aws_account",
    },
    FormSpecId("credentials"): {
        "access_key_id": "my_access_key",
        "secret_access_key": (
            "cmk_postprocessed",
            "explicit_password",
            ("ca2f6299-622f-4339-80bb-14a4ae03bdda", "my_secret_access_key"),
        ),
    },
    FormSpecId("host_data"): {
        "host_name": "my_quick_setup_aws_host",
        "host_path": "a/path/to/my/quick_setup/aws/host",
    },
    FormSpecId("configure_host_and_region"): {
        "regions_to_monitor": {
            "input_context": {},
        },
    },
    FormSpecId("configure_services_to_monitor"): {
        "global_services": {},
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
    FormSpecId("site"): {"site_selection": {}},
    FormSpecId("aws_tags"): {"overall_tags": {}},
}

EXPECTED_PARAMS = {
    "access_key_id": "my_access_key",
    "secret_access_key": (
        "cmk_postprocessed",
        "explicit_password",
        ("ca2f6299-622f-4339-80bb-14a4ae03bdda", "my_secret_access_key"),
    ),
    "regions_to_monitor": {
        "input_context": {},
    },
    "global_services": {},
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
    "overall_tags": {},
}

EXPECTED_PASSWORDS = {"ca2f6299-622f-4339-80bb-14a4ae03bdda": "my_secret_access_key"}


def test_quick_setup_collect_params_from_form_data() -> None:
    load_special_agents()
    assert (
        _collect_params_from_form_data(ALL_FORM_SPEC_DATA, "special_agents:aws") == EXPECTED_PARAMS
    )


def test_quick_setup_collect_passwords_from_form_data() -> None:
    load_special_agents()
    assert (
        _collect_passwords_from_form_data(ALL_FORM_SPEC_DATA, "special_agents:aws")
        == EXPECTED_PASSWORDS
    )
