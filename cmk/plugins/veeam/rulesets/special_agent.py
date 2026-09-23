#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
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
                    title=Title("Username"),
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
            "disable_cert_verification": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Skip TLS certificate validation"),
                    label=Label("Do not verify the server certificate (unsafe)"),
                    help_text=Help(
                        "By default the server's TLS certificate is validated against the "
                        "Checkmk host name. Enable this to connect without verifying the "
                        "certificate, for example when the backup server presents a "
                        "self-signed certificate."
                    ),
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
