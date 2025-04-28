#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast, Literal

from cmk.plugins.vsphere.lib.special_agent import InfoSelection, QueryType
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
        migrate=_migrate_direct_infos,
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
                parameter_form=CascadingSingleChoice(
                    title=Title("Type of query"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name=QueryType.HOST_SYSTEM,
                            title=Title("Queried host is a ESXi host (vCenter integrated)"),
                            parameter_form=_info_form_for_host(QueryType.HOST_SYSTEM),
                        ),
                        CascadingSingleChoiceElement(
                            name=QueryType.VCENTER,
                            title=Title("Queried host is a vCenter"),
                            parameter_form=_info_form_for_host(QueryType.VCENTER),
                        ),
                        CascadingSingleChoiceElement(
                            name=QueryType.STANDALONE,
                            title=Title(
                                "Queried host is a ESXi host (Standalone / not vCenter integrated)"
                            ),
                            parameter_form=_info_form_for_host(QueryType.STANDALONE),
                        ),
                    ],
                    prefill=DefaultValue(QueryType.VCENTER),
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
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="hostname",
                            title=Title("Use host name"),
                            parameter_form=FixedValue(value=None),
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
                    migrate=_migrate_ssl,
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


def _default_infos_for_host(query_type: QueryType) -> list[InfoSelection]:
    match query_type:
        case QueryType.HOST_SYSTEM:
            return ["hostsystem", "counters"]
        case _:
            return ["hostsystem", "virtualmachine", "datastore", "counters"]


def _info_form_for_host(query_type: QueryType) -> MultipleChoice:
    default = _default_infos_for_host(query_type)
    return MultipleChoice(
        title=Title("Retrieve information about..."),
        elements=[
            MultipleChoiceElement(name="hostsystem", title=Title("Host Systems")),
            MultipleChoiceElement(name="virtualmachine", title=Title("Virtual Machines")),
            MultipleChoiceElement(name="datastore", title=Title("Datastores")),
            MultipleChoiceElement(name="counters", title=Title("Performance counters")),
            MultipleChoiceElement(name="licenses", title=Title("License Usage")),
        ],
        prefill=DefaultValue(default),
    )


def _migrate_direct_infos(x: object) -> dict[str, object]:
    x = cast(dict[str, object], x)
    infos = x.pop("infos", [])
    query_type = x["direct"]

    match query_type:
        case QueryType():
            x["direct"] = (query_type, infos)
        case str():
            x["direct"] = (QueryType(query_type), infos)
        case True:
            x["direct"] = (
                QueryType.HOST_SYSTEM,
                infos or _default_infos_for_host(QueryType.HOST_SYSTEM),
            )
        case False:
            x["direct"] = (QueryType.VCENTER, infos or _default_infos_for_host(QueryType.VCENTER))

    return x


def _migrate_ssl(
    value: object,
) -> (
    tuple[Literal["deactivated"], None]
    | tuple[Literal["hostname"], None]
    | tuple[Literal["custom_hostname"], str]
):
    match value:
        case tuple():
            return value
        case False:
            return ("deactivated", None)
        case True:
            return ("hostname", None)
        case str():
            return ("custom_hostname", value)
        case _:
            raise TypeError(value)


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
