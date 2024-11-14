#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
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
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    SingleChoice,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs._basic import SingleChoiceElement
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("VMware ESX via vSphere"),
        help_text=Help(
            "This rule allows monitoring of VMware ESX via the vSphere API. "
            "You can configure your connection settings here.",
        ),
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("vSphere User name"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("vSphere secret"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "direct": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    migrate=_migrate_direct,
                    title=Title("Type of query"),
                    elements=[
                        SingleChoiceElement(
                            name="host_system",
                            title=Title("Queried host is a host system"),
                        ),
                        SingleChoiceElement(
                            name="vcenter",
                            title=Title("Queried host is the vCenter"),
                        ),
                    ],
                ),
            ),
            "tcp_port": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("TCP Port number"),
                    help_text=Help("Port number for HTTPS connection to vSphere"),
                    prefill=DefaultValue(443),
                    custom_validate=(validators.NetworkPort(),),
                ),
            ),
            "ssl": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("SSL certificate checking"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="deactivated",
                            title=Title("Deactivated"),
                            parameter_form=FixedValue(value=False),
                        ),
                        CascadingSingleChoiceElement(
                            name="hostname",
                            title=Title("Use host name"),
                            parameter_form=FixedValue(value=True),
                        ),
                        CascadingSingleChoiceElement(
                            name="custom_hostname",
                            title=Title("Use other host name"),
                            parameter_form=String(
                                help_text=Help(
                                    "Use a custom name for the SSL certificate validation"
                                ),
                                macro_support=True,
                            ),
                        ),
                    ],
                    prefill=DefaultValue("hostname"),
                ),
                required=True,
            ),
            "timeout": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connect timeout"),
                    help_text=Help(
                        "The network timeout in seconds when communicating with vSphere or "
                        "to the Checkmk Agent. The default is 60 seconds. Please note that this "
                        "is not a total timeout but is applied to each individual network transation."
                    ),
                    prefill=DefaultValue(60),
                    custom_validate=(validators.NumberInRange(min_value=1),),
                    unit_symbol="seconds",
                ),
            ),
            "infos": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    title=Title("Retrieve information about..."),
                    elements=[
                        MultipleChoiceElement(name="hostsystem", title=Title("Host Systems")),
                        MultipleChoiceElement(
                            name="virtualmachine", title=Title("Virtual Machines")
                        ),
                        MultipleChoiceElement(name="datastore", title=Title("Datastores")),
                        MultipleChoiceElement(name="counters", title=Title("Performance counters")),
                        MultipleChoiceElement(name="licenses", title=Title("License Usage")),
                    ],
                    prefill=DefaultValue(["hostsystem", "virtualmachine", "datastore", "counters"]),
                ),
            ),
            "skip_placeholder_vms": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Placeholder VMs"),
                    label=Label("Do not monitor placeholder VMs"),
                    prefill=DefaultValue(True),
                    help_text=Help(
                        "Placeholder VMs are created by the Site Recovery Manager (SRM) and act as backup "
                        "virtual machines in case the default VM is unable to start. This option tells the "
                        "vSphere agent to exclude placeholder VMs in its output."
                    ),
                ),
            ),
            "ignore_templates": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Templates"),
                    label=Label("Do not monitor VM templates"),
                    prefill=DefaultValue(False),
                    help_text=Help(
                        "A template is created by converting a stopped VM. It cannot be started or modified "
                        "without converting or cloning it back to a VM. This option tells the vSphere agent "
                        "to exclude template VMs in its output."
                    ),
                ),
            ),
            "host_pwr_display": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    migrate=_migrate_pwr_display,
                    title=Title("Display ESX Host power state on"),
                    elements=[
                        SingleChoiceElement(
                            "host", Title("The queried ESX system (vCenter / Host)")
                        ),
                        SingleChoiceElement("esxhost", Title("The ESX Host")),
                        SingleChoiceElement("vm", Title("The virtual machine")),
                    ],
                    prefill=DefaultValue("host"),
                ),
            ),
            "vm_pwr_display": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    migrate=_migrate_pwr_display,
                    title=Title("Display VM power state <i>additionally</i> on"),
                    help_text=Help(
                        "The power state can be displayed additionally either "
                        "on the ESX host or the VM. This will result in services "
                        "for <i>both</i> the queried system and the ESX host / VM. "
                        "By disabling the unwanted services it is then possible "
                        "to configure where the services are displayed."
                    ),
                    elements=[
                        SingleChoiceElement(
                            "host", Title("The queried ESX system (vCenter / Host)")
                        ),
                        SingleChoiceElement("esxhost", Title("The ESX Host")),
                        SingleChoiceElement("vm", Title("The virtual machine")),
                    ],
                    prefill=DefaultValue("host"),
                ),
            ),
            "snapshots_on_host": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("VM snapshot summary"),
                    label=Label("Display snapshot summary on ESX hosts"),
                    prefill=DefaultValue(False),
                    help_text=Help(
                        "By default the snapshot summary service is displayed on the vCenter. "
                        "Users who run an ESX host on its own or do not include their vCenter in the "
                        "monitoring can choose to display the snapshot summary on the ESX host itself."
                    ),
                ),
            ),
            "vm_piggyname": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("Piggyback name of virtual machines"),
                    elements=[
                        SingleChoiceElement(
                            "alias", Title("Use the name specified in the ESX system")
                        ),
                        SingleChoiceElement(
                            "hostname",
                            Title("Use the VMs host name if set, otherwise fall back to ESX name"),
                        ),
                    ],
                    prefill=DefaultValue("alias"),
                ),
            ),
            "spaces": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Spaces in host names"),
                    elements=[
                        SingleChoiceElement("cut", Title("Cut everything after first space")),
                        SingleChoiceElement("underscore", Title("Replace with underscores")),
                    ],
                    prefill=DefaultValue("underscore"),
                ),
            ),
        },
    )


def _migrate_direct(value: object) -> str:
    if value is True:
        return "host_system"
    return "vcenter"


def _migrate_pwr_display(value: object) -> str:
    if value is None:
        return "host"
    return str(value)


rule_spec_special_agent_vsphere = SpecialAgent(
    name="vsphere",
    title=Title("VMware ESX via vSphere"),
    topic=Topic.CLOUD,
    parameter_form=parameter_form,
    help_text=Help("Monitoring VMWare ESXi"),
)
