#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, ListChoice, Password, TextInput, Transform


def _factory_default_special_agents_emcvnx():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_emcvnx():
    return Dictionary(
        title=_("EMC VNX storage systems"),
        help=_(
            "This rule selects the EMC VNX agent instead of the normal Check_MK Agent "
            "and allows monitoring of EMC VNX storage systems by calling naviseccli "
            "commandline tool locally on the monitoring system. Make sure it is installed "
            "and working. You can configure your connection settings here."
        ),
        elements=[
            (
                "user",
                TextInput(
                    title=_("EMC VNX admin user name"),
                    allow_empty=True,
                    help=_(
                        "If you leave user name and password empty, the special agent tries to "
                        "authenticate against the EMC VNX device by Security Files. "
                        "These need to be created manually before using. Therefor run as "
                        "instance user (if using OMD) or Nagios user (if not using OMD) "
                        "a command like "
                        "<tt>naviseccli -AddUserSecurity -scope 0 -password PASSWORD -user USER</tt> "
                        "This creates <tt>SecuredCLISecurityFile.xml</tt> and "
                        "<tt>SecuredCLIXMLEncrypted.key</tt> in the home directory of the user "
                        "and these files are used then."
                    ),
                ),
            ),
            (
                "password",
                Password(
                    title=_("EMC VNX admin user password"),
                    allow_empty=True,
                ),
            ),
            (
                "infos",
                Transform(
                    valuespec=ListChoice(
                        choices=[
                            ("disks", _("Disks")),
                            ("hba", _("iSCSI HBAs")),
                            ("hwstatus", _("Hardware status")),
                            ("raidgroups", _("RAID groups")),
                            ("agent", _("Model and revsion")),
                            ("sp_util", _("Storage processor utilization")),
                            ("writecache", _("Write cache state")),
                            ("mirrorview", _("Mirror views")),
                            ("storage_pools", _("Storage pools")),
                        ],
                        default_value=[
                            "disks",
                            "hba",
                            "hwstatus",
                        ],
                        allow_empty=False,
                    ),
                    title=_("Retrieve information about..."),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_emcvnx(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:emcvnx",
        valuespec=_valuespec_special_agents_emcvnx,
    )
)
