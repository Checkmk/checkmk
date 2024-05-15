#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from .checktestlib import SpecialAgent


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "access_key_id": "strawberry",
                "secret_access_key": ("password", "strawberry098"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_port": 22,
                    "proxy_user": "banana",
                    "proxy_password": ("password", "banana123"),
                },
                "access": {},
                "global_services": {
                    "ce": None,
                },
                "regions": [],
                "services": {
                    "ec2": {
                        "selection": "all",
                        "limits": True,
                    },
                    "ebs": {
                        "selection": "all",
                        "limits": True,
                    },
                },
                "piggyback_naming_convention": "checkmk_mix",
            },
            [
                "--access-key-id",
                "strawberry",
                "--secret-access-key",
                "strawberry098",
                "--proxy-host",
                "1.1.1",
                "--proxy-port",
                "22",
                "--proxy-user",
                "banana",
                "--proxy-password",
                "banana123",
                "--global-services",
                "ce",
                "--services",
                "ebs",
                "ec2",
                "--ec2-limits",
                "--ebs-limits",
                "--hostname",
                "testhost",
                "--piggyback-naming-convention",
                "checkmk_mix",
            ],
            id="explicit_passwords",
        ),
        pytest.param(
            {
                "access_key_id": "strawberry",
                "secret_access_key": ("store", "strawberry098"),
                "proxy_details": {
                    "proxy_host": "1.1.1",
                    "proxy_user": "banana",
                    "proxy_password": ("store", "banana123"),
                },
                "access": {},
                "global_services": {},
                "regions": [],
                "services": {},
                "piggyback_naming_convention": "checkmk_mix",
            },
            [
                "--access-key-id",
                "strawberry",
                "--secret-access-key",
                ("store", "strawberry098", "%s"),
                "--proxy-host",
                "1.1.1",
                "--proxy-user",
                "banana",
                "--proxy-password",
                ("store", "banana123", "%s"),
                "--hostname",
                "testhost",
                "--piggyback-naming-convention",
                "checkmk_mix",
            ],
            id="passwords_from_store",
        ),
        pytest.param(
            # the value was added before porting to the new server_side_calls api.
            # it just documents the behaviour before the change took place,
            # no sanity check was made if those values can be useful in a production setup.
            {
                "overall_tags": [["ut-key", ["ut-value"]]],
                "services": {
                    # _get_services_config and _get_tag_options
                    "elb": {
                        "selection": (
                            "tags",
                            [("ut_selection_tag_key", ["ut_selection_tag_value"])],
                        )
                    },
                    "elbv2": {
                        "selection": (
                            "tags",
                            [],
                        )
                    },
                    "rds": {
                        "selection": (
                            "names",
                            ["ut_selection_name_1", "ut_selection_name_2"],
                        )
                    },
                    # special treatment of certain services?
                    "cloudwatch": {"alarms": ("ut_ignored", ["ut_cloudwatch_alarms_tuple_1"])},
                    "s3": {"requests": None},  # None if the option is active
                    "wafv2": {"cloudfront": None},  # same here
                },
                "global_services": {
                    "cloudfront": {
                        "host_assignment": "ut_cloudfront_host_assignment",
                    }
                },
                "access": {
                    "global_service_region": "ut_global_service_region",
                    "role_arn_id": ["ut_role_arn_id_1", "ut_role_arn_id_2"],
                },
                "regions": ["ut_region_1"],
                # mandatory params:
                "access_key_id": "ut_access_key_id",
                "secret_access_key": ("store", "ut_secret_access_key_store"),
                "piggyback_naming_convention": "ut_piggyback_naming_convention",
            },
            [
                "--access-key-id",
                "ut_access_key_id",
                "--secret-access-key",
                ("store", "ut_secret_access_key_store", "%s"),
                "--global-service-region",
                "ut_global_service_region",
                "--assume-role",
                "--role-arn",
                "ut_role_arn_id_1",
                "--external-id",
                "ut_role_arn_id_2",
                "--regions",
                "ut_region_1",
                "--global-services",
                "cloudfront",
                "--services",
                "cloudwatch_alarms",
                "elb",
                "elbv2",
                "rds",
                "s3",
                "wafv2",
                "--elb-tag-key",
                "ut_selection_tag_key",
                "--elb-tag-values",
                "ut_selection_tag_value",
                "--rds-names",
                "ut_selection_name_1",
                "ut_selection_name_2",
                "--s3-requests",
                "--cloudwatch-alarms",
                "ut_cloudwatch_alarms_tuple_1",
                "--wafv2-cloudfront",
                "--cloudfront-host-assignment",
                "ut_cloudfront_host_assignment",
                "--overall-tag-key",
                "ut-key",
                "--overall-tag-values",
                "ut-value",
                "--hostname",
                "testhost",
                "--piggyback-naming-convention",
                "ut_piggyback_naming_convention",
            ],
            id="get more coverage",
        ),
    ],
)
def test_aws_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[Any],
) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_aws")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args
