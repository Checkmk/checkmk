#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from typing import Final

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
    List,
    MatchingScope,
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

# Note: the first element of the tuple should match the id of the metric specified in ALL_METRICS
# in the azure special agent
_AZURE_SERVICES: Final = [
    ("users_count", Title("Users in Entra ID")),
    ("ad_connect", Title("Entra Connect Sync")),
    ("app_registrations", Title("App Registrations")),
    ("usage_details", Title("Usage Details")),
    ("Microsoft.Compute/virtualMachines", Title("Virtual Machines")),
    ("Microsoft.Network/virtualNetworkGateways", Title("vNet Gateway")),
    ("Microsoft.Sql/servers/databases", Title("SQL Databases")),
    ("Microsoft.Storage/storageAccounts", Title("Storage")),
    ("Microsoft.Web/sites", Title("Web Servers (IIS)")),
    ("Microsoft.DBforMySQL/servers", Title("Database for MySQL single server")),
    (
        "Microsoft.DBforMySQL/flexibleServers",
        Title("Database for MySQL flexible server"),
    ),
    (
        "Microsoft.DBforPostgreSQL/servers",
        Title("Database for PostgreSQL single server"),
    ),
    (
        "Microsoft.DBforPostgreSQL/flexibleServers",
        Title("Database for PostgreSQL flexible server"),
    ),
    ("Microsoft.Network/trafficmanagerprofiles", Title("Traffic Manager")),
    ("Microsoft.Network/loadBalancers", Title("Load Balancer")),
    ("Microsoft.Network/azureFirewalls", Title("Azure Firewalls")),
]

try:
    from .nonfree.ultimate.azure_services import (  # type: ignore[import-not-found, unused-ignore]
        NONFREEED_AZURE_SERVICES,
    )

    _AZURE_SERVICES.extend(NONFREEED_AZURE_SERVICES)
except ImportError:
    pass


def _azure_service_name_to_valid_formspec(azure_service_name: str) -> str:
    return azure_service_name.replace("Microsoft.", "Microsoft_").replace("/", "_slash_")


def get_azure_service_prefill() -> list[str]:
    return [
        _azure_service_name_to_valid_formspec(s[0])
        for s in _AZURE_SERVICES
        if s[0] not in {"users_count", "ad_connect", "app_registrations"}
    ]


def get_azure_services_elements() -> Sequence[MultipleChoiceElement]:
    return [
        MultipleChoiceElement(
            name=_azure_service_name_to_valid_formspec(service_id),
            title=service_name,
        )
        for service_id, service_name in _AZURE_SERVICES
    ]


def _special_agents_azure_explicit_config() -> DictElement:
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
            title=Title("Explicitly specified groups"),
            add_element_label=Label("Add resource group"),
        )
    )


def _special_agents_azure_tag_based_config_resources() -> DictElement:
    return DictElement(
        parameter_form=List(
            custom_validate=(validators.LengthInRange(min_value=1),),
            element_template=Dictionary(
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
            title=Title("Resources matching tag based criteria"),
            add_element_label=Label("Add resource tag"),
            help_text=Help(
                "Add the tags you want to use to filter the resources. "
                "Only resources with every tags matching, will be monitored."
            ),
        ),
    )


def _special_agents_azure_tag_based_config_subscriptions() -> List:
    return List(
        custom_validate=(validators.LengthInRange(min_value=1),),
        element_template=Dictionary(
            elements={
                "tag": DictElement(
                    parameter_form=String(
                        title=Title("The subscription tag"),
                        custom_validate=(validators.LengthInRange(min_value=1),),
                        field_size=FieldSize.LARGE,
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
                                    field_size=FieldSize.LARGE,
                                ),
                            ),
                        ],
                        prefill=DefaultValue("exists"),
                    ),
                    required=True,
                ),
            },
        ),
        title=Title("Subscriptions matching tag based criteria"),
        add_element_label=Label("Add subscription tag"),
        help_text=Help(
            "Add the tags you want to use to filter the subscriptions. "
            "Only subscriptions with every tags matching, will be monitored."
        ),
    )


def configuration_authentication() -> Mapping[str, DictElement]:
    return {
        "subscription": DictElement(
            parameter_form=CascadingSingleChoice(
                title=Title("Subscriptions to monitor"),
                help_text=Help(
                    "Select the subscriptions containing the ARM resources you want to monitor."
                    "If you do not wish to monitor ARM resources, select 'Do not monitor subscriptions.'"
                    "If you proceed with a subscription, you will be able to choose specific resources to monitor in the next step."
                ),
                elements=[
                    CascadingSingleChoiceElement(
                        name="no_subscriptions",
                        title=Title("Do not monitor subscriptions"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="explicit_subscriptions",
                        title=Title("Explicit list of subscription IDs"),
                        parameter_form=List(
                            title=Title("Explicitly specify subscription IDs"),
                            element_template=String(macro_support=True, field_size=FieldSize.LARGE),
                            custom_validate=(validators.LengthInRange(min_value=1),),
                            editable_order=False,
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="all_subscriptions",
                        title=Title("Monitor all subscriptions"),
                        parameter_form=FixedValue(value=None),
                    ),
                    CascadingSingleChoiceElement(
                        name="tag_matching_subscriptions",
                        title=Title("Tag matching subscriptions"),
                        parameter_form=_special_agents_azure_tag_based_config_subscriptions(),
                    ),
                ],
                prefill=DefaultValue("no_subscriptions"),
            ),
            required=True,
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
                title=Title("Client Secret"),
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
            required=True,
        ),
        "authority": DictElement(
            parameter_form=SingleChoice(
                title=Title("Authority"),
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
        "proxy": DictElement(
            parameter_form=Proxy(
                title=Title("HTTP proxy"),
            ),
        ),
    }


def configuration_services() -> Mapping[str, DictElement]:
    return {
        "services": DictElement(
            parameter_form=MultipleChoice(
                title=Title("Azure services to monitor"),
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


def configuration_advanced() -> Mapping[str, DictElement]:
    return {
        "safe_hostnames": DictElement(
            parameter_form=BooleanChoice(
                label=Label("Enable safe host names"),
                help_text=Help(
                    "Enabling this option lets Checkmk create safe host names for piggyback hosts. "
                    "This avoids conflicts caused by entities having the same name in Azure, which could lead to monitoring data "
                    "being overwritten or lost. The option works by appending a unique hash to the Checkmk piggyback host names "
                    "(Example: 'my-vm-1a2b3c4d'). Enable this if you have subscriptions, resources, or resource groups "
                    "with the same name across multiple Azure tenants or subscriptions."
                ),
                prefill=DefaultValue(False),
            ),
            required=True,
        ),
        "config": DictElement(
            parameter_form=Dictionary(
                title=Title("Retrieve information"),
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
                    "tag_based": _special_agents_azure_tag_based_config_resources(),
                },
            ),
            required=True,
        ),
        "filter_tags": DictElement(
            parameter_form=CascadingSingleChoice(
                title=Title("Filter Azure tags imported as host/service labels"),
                help_text=Help(
                    "Enable this option to import Azure tags as host/service labels. "
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
                        name="filter_tags",
                        title=Title("Filter valid tags by key pattern"),
                        parameter_form=RegularExpression(
                            custom_validate=(validators.LengthInRange(min_value=1),),
                            predefined_help_text=MatchingScope.INFIX,
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="dont_import_tags",
                        title=Title("Do not import tags"),
                        parameter_form=FixedValue(value=None),
                    ),
                ],
                prefill=DefaultValue("filter_tags"),
            ),
        ),
    }


def formspec() -> Dictionary:
    return Dictionary(
        elements={
            **configuration_authentication(),
            **configuration_services(),
            **configuration_advanced(),
        },
    )


rule_spec_azure = SpecialAgent(
    name="azure_v2",
    title=Title("Azure"),
    help_text=Help(
        "To monitor Azure resources add this datasource to <b>one</b> host. "
        "The data will be transported using the piggyback mechanism, so make "
        "sure to create one host for every monitored resource group. You can "
        "learn about the discovered groups in the <i>Azure Agent Info</i> "
        "service of the host owning the datasource program."
    ),
    topic=Topic.CLOUD,
    parameter_form=formspec,
)
