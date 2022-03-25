#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    ListOf,
    ListOfStrings,
    Password,
    TextInput,
    Tuple,
)


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
                        ("value", _("is"), TextInput(title=_("Tag value"), allow_empty=False)),
                    ],
                ),
            ],
        ),
        title=_("resources matching tag based criteria"),
        allow_empty=False,
        add_label=_("Add resource tag"),
    )


def _valuespec_special_agents_azure():
    return Dictionary(
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
                Password(
                    title=_("Client Secret"),
                    allow_empty=False,
                    size=45,
                ),
            ),
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
                        ("tag_based", _special_agents_azure_azure_tag_based_config()),
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
                        " as for any other resource. If the VM is present in your "
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
                "sequential",
                DropdownChoice(
                    title=_("Force agent to run in single thread"),
                    help=_(
                        "Check this to turn off multiprocessing."
                        " Recommended for debugging purposes only."
                    ),
                    choices=[
                        (False, _("Run agent multithreaded")),
                        (True, _("Run agent in single thread")),
                    ],
                ),
            ),
        ],
        optional_keys=["subscription", "piggyback_vms", "sequential"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:azure",
        valuespec=_valuespec_special_agents_azure,
    )
)
