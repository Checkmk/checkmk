#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Final

from cmk.ccc.version import Edition, edition

from cmk.utils import paths

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    MatchingScope,
    migrate_to_password,
    migrate_to_proxy,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    Proxy,
    RegularExpression,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

# Note: the first element of the tuple should match the id of the metric specified in ALL_SERVICES
# in the azure special agent
RAW_AZURE_SERVICES: Final = [
    ("users_count", Title("Users in the Active Directory")),
    ("ad_connect", Title("AD Connect Sync")),
    ("app_registrations", Title("App Registrations")),
    ("usage_details", Title("Usage Details")),
    ("Microsoft.Compute/virtualMachines", Title("Virtual Machines")),
    ("Microsoft.Network/virtualNetworkGateways", Title("vNet Gateway")),
    ("Microsoft.Sql/servers/databases", Title("SQL Databases")),
    ("Microsoft.Storage/storageAccounts", Title("Storage")),
    ("Microsoft.Web/sites", Title("Web Servers (IIS)")),
    ("Microsoft.DBforMySQL/servers", Title("Database for MySQL single server")),
    ("Microsoft.DBforMySQL/flexibleServers", Title("Database for MySQL flexible server")),
    ("Microsoft.DBforPostgreSQL/servers", Title("Database for PostgreSQL single server")),
    ("Microsoft.DBforPostgreSQL/flexibleServers", Title("Database for PostgreSQL flexible server")),
    ("Microsoft.Network/trafficmanagerprofiles", Title("Traffic Manager")),
    ("Microsoft.Network/loadBalancers", Title("Load Balancer")),
]

CCE_AZURE_SERVICES: Final = [
    ("Microsoft.RecoveryServices/vaults", Title("Recovery Services Vault")),
    ("Microsoft.Network/applicationGateways", Title("Application Gateway")),
]


def get_azure_services() -> Sequence[tuple[str, Title]]:
    if edition(paths.omd_root) in (Edition.CME, Edition.CCE, Edition.CSE):
        return RAW_AZURE_SERVICES + CCE_AZURE_SERVICES
    return RAW_AZURE_SERVICES


def get_azure_service_prefill() -> list[str]:
    return [
        s[0].replace("Microsoft.", "Microsoft_").replace("/", "_slash_")
        for s in get_azure_services()
        if s[0] not in {"users_count", "ad_connect", "app_registrations"}
    ]


def get_azure_services_elements() -> Sequence[MultipleChoiceElement]:
    return [
        MultipleChoiceElement(
            name=service_id.replace("Microsoft.", "Microsoft_").replace("/", "_slash_"),
            title=service_name,
        )
        for service_id, service_name in get_azure_services()
    ]


def _special_agents_azure_explicit_config():
    return DictElement(
        parameter_form=List(
            element_template=Dictionary(
                elements={
                    "group_name": DictElement(
                        parameter_form=String(
                            title=Title("Name of the resource group"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                        required=True,
                    ),
                    "resources": DictElement(
                        parameter_form=List(
                            title=Title("Explicitly specify resources"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                            element_template=String(
                                title=Title("Name of the resource"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                    ),
                },
            ),
            title=Title("explicitly specified groups"),
            add_element_label=Label("Add resource group"),
        )
    )


def _migrate_tag_based_config(values: object) -> dict:
    if isinstance(values, dict):
        return values
    if isinstance(values, tuple):
        value = values[1]
        if isinstance(value, str) and value == "exists":
            return {"tag": values[0], "condition": ("exists", None)}
        if isinstance(value, tuple) and value[0] == "value":
            return {"tag": values[0], "condition": ("equals", value[1])}
    raise TypeError(values)


def _special_agents_azure_tag_based_config():
    return DictElement(
        parameter_form=List(
            custom_validate=(validators.LengthInRange(min_value=1),),
            element_template=Dictionary(
                migrate=_migrate_tag_based_config,
                elements={
                    "tag": DictElement(
                        parameter_form=String(
                            title=Title("The resource tag"),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                        ),
                        required=True,
                    ),
                    "condition": DictElement(
                        parameter_form=CascadingSingleChoice(
                            title=None,
                            elements=[
                                CascadingSingleChoiceElement(
                                    name="exists",
                                    title=Title("exists"),
                                    parameter_form=FixedValue(value=None),
                                ),
                                CascadingSingleChoiceElement(
                                    name="equals",
                                    title=Title("is"),
                                    parameter_form=String(
                                        title=Title("Tag value"),
                                    ),
                                ),
                            ],
                            prefill=DefaultValue("exists"),
                        ),
                        required=True,
                    ),
                },
            ),
            title=Title("resources matching tag based criteria"),
            add_element_label=Label("Add resource tag"),
        )
    )


def _migrate_services_to_monitor(values: object) -> list[str]:
    if isinstance(values, list):
        valid_choices = {s[0] for s in get_azure_services()}
        # silently drop values that are only valid in CCE if we're CEE now.
        valid_values = [value for value in values if value in valid_choices]
        return [
            value.replace("Microsoft.", "Microsoft_").replace("/", "_slash_")
            for value in valid_values
        ]
    raise TypeError(values)


def _get_services_fs() -> Mapping[str, DictElement]:
    return {
        "services": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Azure services to monitor"),
                migrate=_migrate_services_to_monitor,
                elements=get_azure_services_elements(),
                # users_count, ad_connect and app_registration are disabled by default because they
                # require special permissions on the Azure app (Graph API permissions + admin consent).
                prefill=DefaultValue(get_azure_service_prefill()),
                help_text=Help(
                    "Select which Azure services to monitor.\n"
                    "In case you want to monitor 'Users in the Active Directory', 'AD Connect Sync',"
                    " or 'App Registrations' you will need to grant the 'Directory.Read.All' graph "
                    "permission to the Azure app and to grant admin consent to it."
                ),
            ),
            required=True,
        ),
    }


def _migrate_authority(value: object) -> str:
    if value == "global":
        return "global_"
    if isinstance(value, str):
        return value
    raise TypeError(value)


def _formspec() -> Dictionary:
    return Dictionary(
        elements={
            "authority": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Authority"),
                    migrate=_migrate_authority,
                    elements=[
                        SingleChoiceElement(name="global_", title=Title("Global")),
                        SingleChoiceElement(name="china", title=Title("China")),
                    ],
                    prefill=DefaultValue("global_"),
                    help_text=Help(
                        "Specify the authority you want to connect to:"
                        "<ul>"
                        "<li>Global: Login into 'https://login.microsoftonline.com',"
                        " get data from 'https://graph.microsoft.com'</li>"
                        "<li>China: Login into 'https://login.partner.microsoftonline.cn',"
                        " get data from 'https://microsoftgraph.chinacloudapi.cn'</li>"
                        "</ul>"
                    ),
                ),
                required=True,
            ),
            "subscription": DictElement(
                parameter_form=String(
                    title=Title("Subscription ID"),
                )
            ),
            "tenant": DictElement(
                parameter_form=String(
                    title=Title("Tenant ID / Directory ID"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "client": DictElement(
                parameter_form=String(
                    title=Title("Client ID / Application ID"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "secret": DictElement(
                parameter_form=Password(
                    migrate=migrate_to_password,
                    title=Title("Client Secret"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "proxy": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                ),
            ),
            **_get_services_fs(),
            "config": DictElement(
                parameter_form=Dictionary(
                    title=Title("Retrieve information about..."),
                    # Since we introduced this, Microsoft has already reduced the number
                    # of allowed API requests. At the time of this writing (11/2018)
                    # you can find the number here:
                    # https://docs.microsoft.com/de-de/azure/azure-resource-manager/resource-manager-request-limits
                    help_text=Help(
                        "By default, all resources associated to the configured tenant ID"
                        " will be monitored. "
                        "However, since Microsoft limits API calls to %s per hour"
                        " (%s per minute), you can restrict the monitoring to individual"
                        " resource groups and resources."
                    )
                    % ("12000", "200"),
                    elements={
                        "explicit": _special_agents_azure_explicit_config(),
                        "tag_based": _special_agents_azure_tag_based_config(),
                    },
                ),
                required=True,
            ),
            "piggyback_vms": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Map data relating to VMs"),
                    help_text=Help(
                        "By default, data relating to a VM is sent to the group host"
                        " corresponding to the resource group of the VM, the same way"
                        " as for any other resource. If the VM is present in your"
                        " monitoring as a separate host, you can choose to send the data"
                        " to the VM itself."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="grouphost", title=Title("Map data to group host")
                        ),
                        SingleChoiceElement(name="self", title=Title("Map data to the VM itself")),
                    ],
                    prefill=DefaultValue("grouphost"),
                ),
            ),
            "sequential": DictElement(
                parameter_form=SingleChoice(
                    migrate=lambda value: "singlethreaded" if value else "multithreaded",
                    title=Title("Force agent to run in single thread"),
                    help_text=Help(
                        "Check this to turn off multiprocessing."
                        " Recommended for debugging purposes only."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="multithreaded", title=Title("Run agent multithreaded")
                        ),
                        SingleChoiceElement(
                            name="singlethreaded", title=Title("Run agent in single thread")
                        ),
                    ],
                    prefill=DefaultValue("multithreaded"),
                ),
            ),
            "import_tags": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Import tags as host/service labels"),
                    help_text=Help(
                        "By default, Checkmk imports all Azure tags as host/service labels. "
                        "The imported tags are added as host labels for resource groups and "
                        "VMs monitored as hosts and as service labels for resources monitored "
                        "as services. The label syntax is 'cmk/azure/tag/{key}:{value}'.<br>"
                        "Additionally, each host representing a resource group is given the "
                        "host label 'cmk/azure/resource_group:{rg_name}', and VMs monitored as "
                        "hosts are given the host label 'cmk/azure/vm:instance', which is done "
                        "independent of this option.<br>"
                        "You can further restrict the imported tags by specifying a pattern "
                        "which Checkmk searches for in the key of the Azure tag, or you can "
                        "disable the import of Azure tags altogether."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="all_tags",
                            title=Title("Import all valid tags"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="filter_tags",
                            title=Title("Filter valid tags by key pattern"),
                            parameter_form=RegularExpression(
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                predefined_help_text=MatchingScope.INFIX,
                            ),
                        ),
                    ],
                    prefill=DefaultValue("all_tags"),
                ),
            ),
        }
    )


rule_spec_azure = SpecialAgent(
    name="azure",
    title=Title("Microsoft Azure"),
    help_text=Help(
        "To monitor Azure resources add this datasource to <b>one</b> host. "
        "The data will be transported using the piggyback mechanism, so make "
        "sure to create one host for every monitored resource group. You can "
        "learn about the discovered groups in the <i>Azure Agent Info</i> "
        "service of the host owning the datasource program."
    ),
    topic=Topic.CLOUD,
    parameter_form=_formspec,
)
