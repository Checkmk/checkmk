#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.version import Edition, edition

from cmk.utils import paths
from cmk.utils.user import UserId

from cmk.base.server_side_calls import load_special_agents

from cmk.gui.quick_setup.v0_unstable.predefined._common import (
    _collect_params_from_form_data,
    _collect_params_with_defaults_from_form_data,
    _collect_passwords_from_form_data,
)
from cmk.gui.quick_setup.v0_unstable.type_defs import ParsedFormData
from cmk.gui.quick_setup.v0_unstable.widgets import FormSpecId
from cmk.gui.session import UserContext

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
    FormSpecId("site"): {"site_selection": "my_site"},
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

CRE_GLOBAL_SERVICES = {
    "ce": ("none", None),
}
ALL_GLOBAL_SERVICES = {
    **CRE_GLOBAL_SERVICES,
    **{
        "cloudfront": ("none", None),
        "route53": ("none", None),
    },
}
EXPECTED_PARAMS_WITH_DEFAULTS = {
    **EXPECTED_PARAMS,
    **{
        "piggyback_naming_convention": "ip_region_instance",
        "access": {},
        "global_services": (
            CRE_GLOBAL_SERVICES if edition(paths.omd_root) is Edition.CRE else ALL_GLOBAL_SERVICES
        ),
    },
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


def test_quick_setup_collect_params_with_defaults_from_form_data(
    with_user: tuple[UserId, str], patch_theme: None
) -> None:
    load_special_agents()
    with UserContext(with_user[0]):
        assert (
            _collect_params_with_defaults_from_form_data(ALL_FORM_SPEC_DATA, "special_agents:aws")
            == EXPECTED_PARAMS_WITH_DEFAULTS
        )
