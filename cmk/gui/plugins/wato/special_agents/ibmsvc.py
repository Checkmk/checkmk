#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Checkbox, Dictionary, ListChoice, TextInput, Transform
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_ibmsvc():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_ibmsvc():
    return Dictionary(
        title=_("IBM SVC / V7000 storage systems"),
        help=_(
            "This rule set selects the <tt>ibmsvc</tt> agent instead of the normal Check_MK Agent "
            "and allows monitoring of IBM SVC / V7000 storage systems by calling "
            "ls* commands there over SSH. "
            "Make sure you have SSH key authentication enabled for your monitoring user. "
            "That means: The user your monitoring is running under on the monitoring "
            "system must be able to ssh to the storage system as the user you gave below "
            "without password."
        ),
        elements=[
            (
                "user",
                TextInput(
                    title=_("IBM SVC / V7000 user name"),
                    allow_empty=True,
                    help=_(
                        "User name on the storage system. Read only permissions are sufficient."
                    ),
                ),
            ),
            (
                "accept-any-hostkey",
                Checkbox(
                    title=_("Accept any SSH Host Key"),
                    label=_("Accept any SSH Host Key"),
                    default_value=False,
                    help=_(
                        "Accepts any SSH Host Key presented by the storage device. "
                        "Please note: This might be a security issue because man-in-the-middle "
                        "attacks are not recognized! Better solution would be to add the "
                        "SSH Host Key of the monitored storage devices to the .ssh/known_hosts "
                        "file for the user your monitoring is running under (on OMD: the site user)"
                    ),
                ),
            ),
            (
                "infos",
                Transform(
                    valuespec=ListChoice(
                        choices=[
                            ("lshost", _("Hosts Connected")),
                            ("lslicense", _("Licensing Status")),
                            ("lsmdisk", _("MDisks")),
                            ("lsmdiskgrp", _("MDisksGrps")),
                            ("lsnode", _("IO Groups")),
                            ("lsnodestats", _("Node Stats")),
                            ("lssystem", _("System Info")),
                            ("lssystemstats", _("System Stats")),
                            ("lseventlog", _("Event Log")),
                            ("lsportfc", _("FC Ports")),
                            ("lsportsas", _("SAS Ports")),
                            ("lsenclosure", _("Enclosures")),
                            ("lsenclosurestats", _("Enclosure Stats")),
                            ("lsarray", _("RAID Arrays")),
                            ("disks", _("Physical Disks")),
                        ],
                        default_value=[
                            "lshost",
                            "lslicense",
                            "lsmdisk",
                            "lsmdiskgrp",
                            "lsnode",
                            "lsnodestats",
                            "lssystem",
                            "lssystemstats",
                            "lsportfc",
                            "lsenclosure",
                            "lsenclosurestats",
                            "lsarray",
                            "disks",
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
        factory_default=_factory_default_special_agents_ibmsvc(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:ibmsvc",
        valuespec=_valuespec_special_agents_ibmsvc,
    )
)
