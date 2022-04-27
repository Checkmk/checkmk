#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Integer,
    ListChoice,
    TextInput,
    Transform,
)
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_vsphere():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _transform_agent_vsphere(params):
    params.setdefault("skip_placeholder_vms", True)
    params.setdefault("ssl", False)
    params.pop("use_pysphere", None)
    params.setdefault("spaces", "underscore")

    if "snapshots_on_host" not in params:
        params["snapshots_on_host"] = params.pop("snapshot_display", "vCenter") == "esxhost"

    if isinstance(params["direct"], str):
        params["direct"] = "hostsystem" in params["direct"]

    return params


def _valuespec_special_agents_vsphere():
    return Transform(
        valuespec=Dictionary(
            title=_("VMWare ESX via vSphere"),
            help=_(
                "This rule allows monitoring of VMWare ESX via the vSphere API. "
                "You can configure your connection settings here.",
            ),
            elements=[
                (
                    "user",
                    TextInput(
                        title=_("vSphere User name"),
                        allow_empty=False,
                    ),
                ),
                (
                    "secret",
                    IndividualOrStoredPassword(
                        title=_("vSphere secret"),
                        allow_empty=False,
                    ),
                ),
                (
                    "direct",
                    DropdownChoice(
                        title=_("Type of query"),
                        choices=[
                            (True, _("Queried host is a host system")),
                            (False, _("Queried host is the vCenter")),
                        ],
                    ),
                ),
                (
                    "tcp_port",
                    Integer(
                        title=_("TCP Port number"),
                        help=_("Port number for HTTPS connection to vSphere"),
                        default_value=443,
                        minvalue=1,
                        maxvalue=65535,
                    ),
                ),
                (
                    "ssl",
                    Alternative(
                        title=_("SSL certificate checking"),
                        elements=[
                            FixedValue(value=False, title=_("Deactivated"), totext=""),
                            FixedValue(value=True, title=_("Use hostname"), totext=""),
                            TextInput(
                                title=_("Use other hostname"),
                                help=_(
                                    "The IP of the other hostname needs to be the same IP as the host address"
                                ),
                            ),
                        ],
                        default_value=True,
                    ),
                ),
                (
                    "timeout",
                    Integer(
                        title=_("Connect Timeout"),
                        help=_(
                            "The network timeout in seconds when communicating with vSphere or "
                            "to the Check_MK Agent. The default is 60 seconds. Please note that this "
                            "is not a total timeout but is applied to each individual network transation."
                        ),
                        default_value=60,
                        minvalue=1,
                        unit=_("seconds"),
                    ),
                ),
                (
                    "infos",
                    Transform(
                        valuespec=ListChoice(
                            choices=[
                                ("hostsystem", _("Host Systems")),
                                ("virtualmachine", _("Virtual Machines")),
                                ("datastore", _("Datastores")),
                                ("counters", _("Performance Counters")),
                                ("licenses", _("License Usage")),
                            ],
                            default_value=["hostsystem", "virtualmachine", "datastore", "counters"],
                            allow_empty=False,
                        ),
                        forth=lambda v: [x.replace("storage", "datastore") for x in v],
                        title=_("Retrieve information about..."),
                    ),
                ),
                (
                    "skip_placeholder_vms",
                    Checkbox(
                        title=_("Placeholder VMs"),
                        label=_("Do not monitor placeholder VMs"),
                        default_value=True,
                        true_label=_("ignore"),
                        false_label=_("monitor"),
                        help=_(
                            "Placeholder VMs are created by the Site Recovery Manager(SRM) and act as backup "
                            "virtual machines in case the default vm is unable to start. This option tells the "
                            "vsphere agent to exclude placeholder vms in its output."
                        ),
                    ),
                ),
                (
                    "host_pwr_display",
                    DropdownChoice(
                        title=_("Display ESX Host power state on"),
                        choices=[
                            (None, _("The queried ESX system (vCenter / Host)")),
                            ("esxhost", _("The ESX Host")),
                            ("vm", _("The Virtual Machine")),
                        ],
                        default_value=None,
                    ),
                ),
                (
                    "vm_pwr_display",
                    DropdownChoice(
                        title=_("Display VM power state <i>additionally</i> on"),
                        help=_(
                            "The power state can be displayed additionally either "
                            "on the ESX host or the VM. This will result in services "
                            "for <i>both</i> the queried system and the ESX host / VM. "
                            "By disabling the unwanted services it is then possible "
                            "to configure where the services are displayed."
                        ),
                        choices=[
                            (None, _("The queried ESX system (vCenter / Host)")),
                            ("esxhost", _("The ESX Host")),
                            ("vm", _("The Virtual Machine")),
                        ],
                        default_value=None,
                    ),
                ),
                (
                    "snapshots_on_host",
                    Checkbox(
                        title=_("VM snapshot summary"),
                        label=_("Display snapshot summary on ESX hosts"),
                        default_value=False,
                        help=_(
                            "By default the snapshot summary service is displayed on the vCenter. "
                            "Users who run an ESX host on its own or do not include their vCenter in the "
                            "monitoring can choose to display the snapshot summary on the ESX host itself."
                        ),
                    ),
                ),
                (
                    "vm_piggyname",
                    DropdownChoice(
                        title=_("Piggyback name of virtual machines"),
                        choices=[
                            ("alias", _("Use the name specified in the ESX system")),
                            (
                                "hostname",
                                _("Use the VMs hostname if set, otherwise fall back to ESX name"),
                            ),
                        ],
                        default_value="alias",
                    ),
                ),
                (
                    "spaces",
                    DropdownChoice(
                        title=_("Spaces in hostnames"),
                        choices=[
                            ("cut", _("Cut everything after first space")),
                            ("underscore", _("Replace with underscores")),
                        ],
                        default_value="underscore",
                    ),
                ),
            ],
            optional_keys=[
                "tcp_port",
                "timeout",
                "vm_pwr_display",
                "host_pwr_display",
                "vm_piggyname",
            ],
            ignored_keys=["use_pysphere"],
        ),
        forth=_transform_agent_vsphere,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_vsphere(),
        group=RulespecGroupVMCloudContainer,
        name="special_agents:vsphere",
        valuespec=_valuespec_special_agents_vsphere,
    )
)
