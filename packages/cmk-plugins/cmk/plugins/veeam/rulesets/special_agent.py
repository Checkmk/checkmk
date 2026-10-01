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
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

# The section names match the agent's section registry. A service the user
# selects but the agent cannot fetch terminates the agent (see agent_veeam.py).
_SECTION_CHOICES = (
    MultipleChoiceElement(
        name="veeam_server_info", title=Title("Server information (HW/SW inventory)")
    ),
    MultipleChoiceElement(name="veeam_license", title=Title("License")),
    MultipleChoiceElement(name="veeam_backup_jobs", title=Title("Backup jobs")),
    MultipleChoiceElement(name="veeam_backups", title=Title("Backups (per protected machine)")),
    MultipleChoiceElement(name="veeam_replicas", title=Title("Replicas")),
    MultipleChoiceElement(name="veeam_protection_groups", title=Title("Agent protection groups")),
    MultipleChoiceElement(name="veeam_managed_servers", title=Title("Managed servers")),
    MultipleChoiceElement(name="veeam_wan_accelerators", title=Title("WAN accelerators")),
    MultipleChoiceElement(name="veeam_config_backup", title=Title("Configuration backup")),
    MultipleChoiceElement(name="veeam_proxies", title=Title("Backup proxies")),
    MultipleChoiceElement(name="veeam_repositories", title=Title("Backup repositories")),
    MultipleChoiceElement(
        name="veeam_scaleout_repositories", title=Title("Scale-out repositories")
    ),
    MultipleChoiceElement(name="veeam_restore_points", title=Title("Restore points")),
)


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Veeam Backup & Replication"),
        help_text=Help(
            "Monitor a Veeam Backup & Replication server through its REST API. Nothing "
            "is installed on the backup server, so this also works for the Veeam "
            "software appliance, where the Checkmk agent cannot run. "
            "Use a dedicated account whose role can read the data you want to monitor; "
            "some services require a more privileged role, and the agent stops when it "
            "cannot read a service. Do not configure an administrator account: it could "
            "also delete backups, trigger restores and read stored encryption passwords."
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
            "sections": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Services to fetch"),
                    help_text=Help(
                        "Select which data the special agent fetches from the backup "
                        "server. Deselect services you do not need, for example ones your "
                        "monitoring account has no permission for. A service that is "
                        "selected but cannot be fetched makes the agent fail, so that you "
                        "can correct the selection or the permissions."
                    ),
                    elements=_SECTION_CHOICES,
                    prefill=DefaultValue([element.name for element in _SECTION_CHOICES]),
                    show_toggle_all=True,
                    custom_validate=(validators.LengthInRange(min_value=1),),
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
