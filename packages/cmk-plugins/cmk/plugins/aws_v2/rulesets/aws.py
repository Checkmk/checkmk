#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The rule of the aws_v2 special agent.

The rule is put together from the public builders below. The Quick Setup of the new AWS
integration uses the same builders, so that the rule and the Quick Setup stay the same.
"""

# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from typing import Final

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Integer,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)

_GLOBAL_SERVICE_REGIONS: Final = ("us-gov-east-1", "us-gov-west-1", "cn-north-1", "cn-northwest-1")


def _region_to_formspec_name(region: str) -> str:
    # Form spec names must be Python identifiers.
    return region.replace("-", "_")


def _access_key() -> Mapping[str, DictElement]:
    return {
        "access_key_id": DictElement(
            parameter_form=String(
                title=Title("The access key ID for your AWS account"),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
        "secret_access_key": DictElement(
            parameter_form=Password(
                title=Title("The secret access key for your AWS account"),
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
    }


def _assume_role() -> Mapping[str, DictElement]:
    return {
        "role_arn_id": DictElement(
            parameter_form=String(
                title=Title("The ARN of the IAM role to assume"),
                help_text=Help("The Amazon Resource Name (ARN) of the role to assume."),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
        "external_id": DictElement(
            parameter_form=String(
                title=Title("External ID"),
                help_text=Help(
                    "A unique identifier that might be required when you assume a role in another "
                    "account. If the administrator of the account to which the role belongs provided "
                    "you with an external ID, then provide that value in the External ID parameter. "
                ),
                field_size=FieldSize.LARGE,
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
    }


def configuration_authentication() -> Mapping[str, DictElement]:
    return {
        "auth": DictElement(
            parameter_form=CascadingSingleChoice(
                title=Title("Authentication type"),
                help_text=Help(
                    "Monitoring via an IAM role is recommended, however it requires the monitoring "
                    "site to be located on an AWS EC2 instance with the according permissions to "
                    "the accounts to be monitored."
                ),
                elements=[
                    CascadingSingleChoiceElement(
                        name="access_key",
                        title=Title("Access key"),
                        parameter_form=Dictionary(elements=_access_key()),
                    ),
                    CascadingSingleChoiceElement(
                        name="access_key_sts",
                        title=Title("Access key + IAM role"),
                        parameter_form=Dictionary(elements={**_access_key(), **_assume_role()}),
                    ),
                    CascadingSingleChoiceElement(
                        name="sts",
                        title=Title("IAM role (on EC2 instance only)"),
                        parameter_form=Dictionary(elements=_assume_role()),
                    ),
                    CascadingSingleChoiceElement(
                        name="none",
                        title=Title("None (on EC2 instance only)"),
                        parameter_form=FixedValue(value=None),
                    ),
                ],
                prefill=DefaultValue("access_key"),
            ),
            required=True,
        ),
        "global_service_region": DictElement(
            parameter_form=SingleChoice(
                title=Title("Use custom region for global AWS services"),
                help_text=Help(
                    "us-gov-* or cn-* regions have their own global services and may not reach "
                    "the default one."
                ),
                elements=[
                    SingleChoiceElement(
                        name="default", title=Title("default (all normal AWS regions)")
                    ),
                    *(
                        SingleChoiceElement(
                            name=_region_to_formspec_name(region),
                            title=Title("%(region)s") % {"region": region},
                        )
                        for region in _GLOBAL_SERVICE_REGIONS
                    ),
                ],
                prefill=DefaultValue("default"),
            ),
            required=True,
        ),
        "proxy_details": DictElement(
            parameter_form=Dictionary(
                title=Title("Proxy server details"),
                elements={
                    "proxy_host": DictElement(
                        parameter_form=String(
                            title=Title("Proxy host"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                        required=True,
                    ),
                    "proxy_port": DictElement(
                        parameter_form=Integer(
                            title=Title("Port"),
                            custom_validate=(validators.NetworkPort(),),
                        ),
                    ),
                    "proxy_user": DictElement(
                        parameter_form=String(
                            title=Title("Username"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                    ),
                    "proxy_password": DictElement(
                        parameter_form=Password(title=Title("Password")),
                    ),
                },
            ),
        ),
    }
