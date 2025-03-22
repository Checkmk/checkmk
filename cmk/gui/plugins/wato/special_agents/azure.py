#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.version import Edition, edition

from cmk.gui.i18n import _
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListChoice,
    ListOf,
    ListOfStrings,
    Migrate,
    MigrateNotUpdated,
    RegExp,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.wato import (
    HTTPProxyReference,
    MigrateToIndividualOrStoredPassword,
    RulespecGroupVMCloudContainer,
)
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry

# Note: the first element of the tuple should match the id of the metric specified in ALL_SERVICES
# in the azure special agent
RAW_AZURE_SERVICES: Final = [
    ("users_count", _("Users in the Active Directory")),
    ("ad_connect", _("AD Connect Sync")),
    ("app_registrations", _("App Registrations")),
    ("usage_details", _("Usage Details")),
    ("Microsoft.Compute/virtualMachines", _("Virtual Machines")),
    ("Microsoft.Network/virtualNetworkGateways", _("vNet Gateway")),
    ("Microsoft.Sql/servers/databases", _("SQL Databases")),
    ("Microsoft.Storage/storageAccounts", _("Storage")),
    ("Microsoft.Web/sites", _("Web Servers (IIS)")),
    ("Microsoft.DBforMySQL/servers", _("Database for MySQL single server")),
    ("Microsoft.DBforMySQL/flexibleServers", _("Database for MySQL flexible server")),
    ("Microsoft.DBforPostgreSQL/servers", _("Database for PostgreSQL")),
    ("Microsoft.Network/trafficmanagerprofiles", _("Traffic Manager")),
    ("Microsoft.Network/loadBalancers", _("Load Balancer")),
]

CCE_AZURE_SERVICES: Final = [
    ("Microsoft.RecoveryServices/vaults", _("Recovery Services Vault")),
    ("Microsoft.Network/applicationGateways", _("Application Gateway")),
]


def get_azure_services() -> list[tuple[str, str]]:
    if edition() in (Edition.CME, Edition.CCE, Edition.CSE):
        return RAW_AZURE_SERVICES + CCE_AZURE_SERVICES

    return RAW_AZURE_SERVICES


def _special_agents_azure_azure_explicit_config():
    return ListOf(
        valuespec=Dictionary(
            elements=[
                (
                    "group_name",
                    TextInput(
                        title=_("Name of the resource group"),
                        allow_empty=False,
                    ),
                ),
                (
                    "resources",
                    ListOfStrings(
                        title=_("Explicitly specify resources"),
                        allow_empty=False,
                    ),
                ),
            ],
            optional_keys=["resources"],
        ),
        title=_("explicitly specified groups"),
        allow_empty=False,
        add_label=_("Add resource group"),
    )


def _special_agents_azure_azure_tag_based_config():
    return ListOf(
        valuespec=Tuple(
            orientation="horizontal",
            elements=[
                TextInput(
                    title=_("The resource tag"),
                    allow_empty=False,
                ),
                CascadingDropdown(
                    orientation="horizontal",
                    choices=[
                        ("exists", _("exists")),
                        (
                            "value",
                            _("is"),
                            TextInput(title=_("Tag value"), allow_empty=False),
                        ),
                    ],
                ),
            ],
        ),
        title=_("resources matching tag based criteria"),
        allow_empty=False,
        add_label=_("Add resource tag"),
    )


def _migrate_azure_rule_vs(data):
    if "authority" not in data:
        data["authority"] = "global"
    if "services" not in data:
        # Services selection was introduced after Azure monitoring so we want that the users with an
        # older version will have all services enabled as it was before this change
        data["services"] = [service_id for service_id, _service_name in get_azure_services()]
    data.pop("import_tags", None)
    data.pop("sequential", None)
    return data


def _valuespec_special_agents_azure():
    return Migrate(
        Dictionary(
            title=_("Microsoft Azure"),
            help=_(
                "To monitor Azure resources add this datasource to <b>one</b> host. "
                "The data will be transported using the piggyback mechanism, so make "
                "sure to create one host for every monitored resource group. You can "
                "learn about the discovered groups in the <i>Azure Agent Info</i> "
                "service of the host owning the datasource program."
            ),
            # element names starting with "--" will be passed do cmd line w/o parsing!
            elements=[
                (
                    "authority",
                    DropdownChoice(
                        title=_("Authority"),
                        choices=[
                            ("global", _("Global")),
                            ("china", _("China")),
                        ],
                        default="global",
                        help=_(
                            "Specify the authority you want to connect to:"
                            "<ul>"
                            "<li>Global: Login into 'https://login.microsoftonline.com',"
                            " get data from 'https://graph.microsoft.com'</li>"
                            "<li>China: Login into 'https://login.partner.microsoftonline.cn',"
                            " get data from 'https://microsoftgraph.chinacloudapi.cn'</li>"
                            "</ul>"
                        ),
                    ),
                ),
                (
                    "subscription",
                    TextInput(
                        title=_("Subscription ID"),
                        allow_empty=False,
                        size=45,
                    ),
                ),
                (
                    "tenant",
                    TextInput(
                        title=_("Tenant ID / Directory ID"),
                        allow_empty=False,
                        size=45,
                    ),
                ),
                (
                    "client",
                    TextInput(
                        title=_("Client ID / Application ID"),
                        allow_empty=False,
                        size=45,
                    ),
                ),
                (
                    "secret",
                    MigrateToIndividualOrStoredPassword(
                        title=_("Client Secret"),
                        allow_empty=False,
                        size=45,
                    ),
                ),
                (
                    "proxy",
                    HTTPProxyReference(),
                ),
                get_services_vs(),
                (
                    "config",
                    Dictionary(
                        title=_("Retrieve information about..."),
                        # Since we introduced this, Microsoft has already reduced the number
                        # of allowed API requests. At the time of this writing (11/2018)
                        # you can find the number here:
                        # https://docs.microsoft.com/de-de/azure/azure-resource-manager/resource-manager-request-limits
                        help=_(
                            "By default, all resources associated to the configured tenant ID"
                            " will be monitored."
                        )
                        + " "
                        + _(
                            "However, since Microsoft limits API calls to %s per hour"
                            " (%s per minute), you can restrict the monitoring to individual"
                            " resource groups and resources."
                        )
                        % ("12000", "200"),
                        elements=[
                            ("explicit", _special_agents_azure_azure_explicit_config()),
                            (
                                "tag_based",
                                _special_agents_azure_azure_tag_based_config(),
                            ),
                        ],
                    ),
                ),
                (
                    "piggyback_vms",
                    DropdownChoice(
                        title=_("Map data relating to VMs"),
                        help=_(
                            "By default, data relating to a VM is sent to the group host"
                            " corresponding to the resource group of the VM, the same way"
                            " as for any other resource. If the VM is present in your"
                            " monitoring as a separate host, you can choose to send the data"
                            " to the VM itself."
                        ),
                        choices=[
                            ("grouphost", _("Map data to group host")),
                            ("self", _("Map data to the VM itself")),
                        ],
                    ),
                ),
                (
                    "filter_tags",
                    CascadingDropdown(
                        title=("Filter tags imported as host/service labels"),
                        choices=[
                            (
                                "filter_tags",
                                _("Filter valid tags by key pattern"),
                                RegExp(
                                    mode=RegExp.infix,
                                    allow_empty=False,
                                    size=50,
                                ),
                            ),
                            (
                                "dont_import_tags",
                                _("Do not import tags"),
                                FixedValue(None, totext=""),
                            ),
                        ],
                        orientation="horizontal",
                        help=_(
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
                    ),
                ),
            ],
            optional_keys=[
                "subscription",
                "proxy",
                "filter_tags",
                "piggyback_vms",
            ],
        ),
        migrate=_migrate_azure_rule_vs,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name=RuleGroup.SpecialAgents("azure"),
        valuespec=_valuespec_special_agents_azure,
        doc_references={DocReference.AZURE: _("Monitoring Microsoft Azure")},
    )
)


def get_services_vs() -> tuple[str, ValueSpec]:
    valid_choices = {s[0] for s in get_azure_services()}
    return (
        "services",
        MigrateNotUpdated(
            valuespec=ListChoice(
                title=_("Azure services to monitor"),
                choices=get_azure_services(),
                # users_count, ad_connect and app_registration are disabled by default because they
                # require special permissions on the Azure app (Graph API permissions + admin consent).
                default_value=[
                    s[0]
                    for s in get_azure_services()
                    if s[0] not in {"users_count", "ad_connect", "app_registrations"}
                ],
                allow_empty=True,
                help=_(
                    "Select which Azure services to monitor.\n"
                    "In case you want to monitor 'Users in the Active Directory', 'AD Connect Sync',"
                    " or 'App Registrations' you will need to grant the 'Directory.Read.All' graph "
                    "permission to the Azure app and to grant admin consent to it."
                ),
            ),
            # silently drop values that are only valid in CCE if we're CEE now.
            migrate=lambda slist: [s for s in slist if s in valid_choices],
        ),
    )
