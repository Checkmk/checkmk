#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    migrate_to_password,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Backup & Replication"),
        help_text=Help(
            "Monitor a Veeam Backup & Replication server through its REST API. Nothing "
            "is installed on the backup server, so this also works for the Veeam "
            "software appliance, where the Checkmk agent cannot run. "
            "The built-in <tt>Veeam Backup Viewer</tt> role is sufficient. Do not "
            "configure an administrator account: it could also delete backups, trigger "
            "restores and read stored encryption passwords."
        ),
        elements={
            "connection": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Connect to"),
                    help_text=Help(
                        "The address the special agent connects to. Independently of "
                        "this, the TLS certificate is validated against the host name, "
                        "so certificate validation keeps working when connecting to an "
                        "IP address."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="ip_address",
                            title=Title("The IP address of the host"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="host_name",
                            title=Title("The name of the host"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom_address",
                            title=Title("A custom address"),
                            parameter_form=String(
                                # Do not validate against being a _Checkmk_ host name here.
                                # Users may enter an IP address, a legal host name or a
                                # macro such as $HOSTNAME$.
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    ],
                    prefill=DefaultValue("ip_address"),
                ),
            ),
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("TCP port"),
                    help_text=Help("The port the Veeam REST API listens on."),
                    prefill=DefaultValue(9419),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("User name"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "cert_verification": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("TLS certificate validation"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="secure",
                            title=Title("Verify the server certificate"),
                            parameter_form=Dictionary(
                                elements={
                                    "cert_server_name": DictElement(
                                        required=False,
                                        parameter_form=String(
                                            title=Title("TLS certificate host name"),
                                            custom_validate=(
                                                validators.LengthInRange(min_value=1),
                                            ),
                                            help_text=Help(
                                                "The host name the server certificate is "
                                                "validated against. If omitted, the "
                                                "Checkmk host name is used."
                                            ),
                                        ),
                                    ),
                                }
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="insecure",
                            title=Title("Do not verify the server certificate (unsafe)"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue("secure"),
                ),
            ),
        },
    )


rule_spec_special_agent_veeam = SpecialAgent(
    name="veeam",
    title=Title("Veeam Backup & Replication"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
