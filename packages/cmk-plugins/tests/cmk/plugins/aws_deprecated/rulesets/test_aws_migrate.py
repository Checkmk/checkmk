#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.aws_deprecated.server_side_calls.aws_agent_call import AwsParams
from cmk.server_side_calls.v1 import Secret

ACCESS_KEY_ID = "XYZABC123"

PROCESSED_ACCESS_KEY_SECRET = Secret(id=0)

ROLE_ARN_ID = "arn:aws:iam::AWSID:role/Rolename"
EXTERNAL_ID = "UniqueExternalIdFrom-4080-3046-6243"


AUTH_STS = (
    "sts",
    {"role_arn_id": ROLE_ARN_ID, "external_id": EXTERNAL_ID},
)


@pytest.mark.parametrize(
    ["value"],
    [
        pytest.param(
            {
                "access": {},
                "auth": "none",
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthNone",
        ),
        pytest.param(
            {
                "access": {},
                "auth": AUTH_STS,
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthSts",
        ),
        pytest.param(
            {
                "access": {},
                "auth": (
                    "access_key_sts",
                    {
                        "access_key_id": ACCESS_KEY_ID,
                        "secret_access_key": PROCESSED_ACCESS_KEY_SECRET,
                        "role_arn_id": ROLE_ARN_ID,
                        "external_id": EXTERNAL_ID,
                    },
                ),
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthAccessKey",
        ),
        pytest.param(
            {
                "access": {},
                "auth": (
                    "access_key",
                    {
                        "access_key_id": ACCESS_KEY_ID,
                        "secret_access_key": PROCESSED_ACCESS_KEY_SECRET,
                    },
                ),
                "piggyback_naming_convention": "ip_region_instance",
            },
            id="model_validate_AuthAccessKeySts",
        ),
    ],
)
def test_auth_pydantic_model(value: Mapping[str, object]) -> None:
    AwsParams.model_validate(value)
