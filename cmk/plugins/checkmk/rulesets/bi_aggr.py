#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def migrate_credentials(
    params: object,
) -> tuple[Literal["automation"], None] | tuple[Literal["credentials"], Mapping[str, object]]:
    match params:
        case "automation" | ("automation", None):
            return "automation", None
        case "credentials", ((user, secret) | {"user": user, "secret": secret}):
            return "credentials", {"user": user, "secret": secret}
        case "configured", (user, ("password", secret)):
            return "credentials", {"user": user, "secret": secret}
    raise ValueError(params)


def _form_spec_active_checks_bi_aggr() -> Dictionary:
    return Dictionary(
        title=Title("Check State of BI Aggregation"),
        help_text=Help(
            "Connect to the local or a remote monitoring host, which uses Checkmk BI to aggregate "
            "several states to a single BI aggregation, which you want to show up as a single "
            "service."
        ),
        elements={
            "base_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Base URL (OMD Site)"),
                    help_text=Help(
                        "The base URL to the monitoring instance. For example <tt>http://mycheckmk01/mysite</tt>. "
                        "You can use macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this URL to "
                        "make them be replaced by the hosts values."
                    ),
                    field_size=FieldSize.LARGE,
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "aggregation_name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Aggregation name"),
                    help_text=Help(
                        "The name of the aggregation to fetch. It will be added to the service name. You can "
                        "use macros like <tt>$HOSTADDRESS$</tt> and <tt>$HOSTNAME$</tt> within this parameter to "
                        "make them be replaced by the hosts values. The aggregation name is the title in the "
                        "top-level-rule of your BI pack."
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "credentials": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Login credentials"),
                    migrate=migrate_credentials,
                    help_text=Help(
                        "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                        "to exist if you choose this option"
                    ),
                    prefill=DefaultValue("automation"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="automation",
                            title=Title("Use the credentials of the 'automation' user"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="configured",
                            title=Title("Use the following credentials"),
                            parameter_form=Dictionary(
                                elements={
                                    "user": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("Automation user name"),
                                            help_text=Help(
                                                "The name of the automation account to use for fetching the BI aggregation via HTTP."
                                                " Note: You may also set credentials of a standard user account, though it is disadvised."
                                                " Using the credentials of a standard user also requires a valid authentication method set"
                                                " in the optional parameters."
                                            ),
                                        ),
                                    ),
                                    "secret": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("Automation Secret"),
                                            help_text=Help(
                                                "Valid automation secret for the automation user"
                                            ),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                            migrate=migrate_to_password,
                                        ),
                                    ),
                                }
                            ),
                        ),
                    ),
                ),
            ),
            "optional": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Optional parameters"),
                    elements={
                        "auth_mode": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("Authentication mode"),
                                prefill=DefaultValue("header"),
                                elements=[
                                    SingleChoiceElement(
                                        name="header", title=Title("Authorization Header")
                                    ),
                                    SingleChoiceElement(name="basic", title=Title("HTTP Basic")),
                                    SingleChoiceElement(name="digest", title=Title("HTTP Digest")),
                                    # Kerberos auth support was removed with 2.4.0 but kept here to
                                    # show a helpful error message in case a user still has
                                    # configured it. Can be removed with 2.5.
                                    SingleChoiceElement(name="kerberos", title=Title("Kerberos")),
                                ],
                            ),
                        ),
                        "timeout": DictElement(
                            parameter_form=TimeSpan(
                                title=Title("Seconds before connection times out"),
                                displayed_magnitudes=[TimeMagnitude.SECOND],
                                migrate=float,  # type: ignore[arg-type]  # wrong type, but desired behaviour.
                                prefill=DefaultValue(60.0),
                            ),
                        ),
                        "in_downtime": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("State, if BI aggregate is in scheduled downtime"),
                                migrate=lambda x: str(x) if x is not None else "normal",
                                elements=(
                                    SingleChoiceElement(
                                        name="normal",
                                        title=Title("Use normal state, ignore downtime"),
                                    ),
                                    SingleChoiceElement(name="ok", title=Title("Force to be OK")),
                                    SingleChoiceElement(
                                        name="warn",
                                        title=Title("Force to be WARN, if aggregate is not OK"),
                                    ),
                                ),
                            ),
                        ),
                        "acknowledged": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("State, if BI aggregate is acknowledged"),
                                migrate=lambda x: str(x) if x is not None else "normal",
                                elements=(
                                    SingleChoiceElement(
                                        name="normal",
                                        title=Title("Use normal state, ignore acknowledgement"),
                                    ),
                                    SingleChoiceElement(name="ok", title=Title("Force to be OK")),
                                    SingleChoiceElement(
                                        name="warn",
                                        title=Title("Force to be WARN, if aggregate is not OK"),
                                    ),
                                ),
                            ),
                        ),
                        "track_downtimes": DictElement(
                            parameter_form=BooleanChoice(
                                title=Title("Track downtimes"),
                                label=Label("Automatically track downtimes of aggregation"),
                                help_text=Help(
                                    "If this is active, the check will automatically go into downtime "
                                    "whenever the aggregation does. This downtime is also cleaned up "
                                    "automatically when the aggregation leaves downtime. "
                                    "Downtimes you set manually for this check are unaffected."
                                ),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_active_check_bi_aggr = ActiveCheck(
    name="bi_aggr",
    title=Title("Check State of BI Aggregation"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec_active_checks_bi_aggr,
    is_deprecated=True,
)
