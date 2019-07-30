#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    Float,
    Integer,
    ListChoice,
    Optional,
    Percentage,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersStorage,
    CheckParameterRulespecWithItem,
    rulespec_registry,
    HostRulespec,
)

_brocade_fcport_adm_choices = [
    (1, 'online(1)'),
    (2, 'offline(2)'),
    (3, 'testing(3)'),
    (4, 'faulty(4)'),
]

_brocade_fcport_op_choices = [
    (0, 'unkown(0)'),
    (1, 'online(1)'),
    (2, 'offline(2)'),
    (3, 'testing(3)'),
    (4, 'faulty(4)'),
]

_brocade_fcport_phy_choices = [
    (1, 'noCard(1)'),
    (2, 'noTransceiver(2)'),
    (3, 'laserFault(3)'),
    (4, 'noLight(4)'),
    (5, 'noSync(5)'),
    (6, 'inSync(6)'),
    (7, 'portFault(7)'),
    (8, 'diagFault(8)'),
    (9, 'lockRef(9)'),
    (10, 'validating(10)'),
    (11, 'invalidModule(11)'),
    (14, 'noSigDet(14)'),
    (255, 'unkown(255)'),
]


@rulespec_registry.register
class RulespecBrocadeFcportInventory(HostRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "brocade_fcport_inventory"

    @property
    def match_type(self):
        return "dict"

    @property
    def valuespec(self):
        return Dictionary(
            title=_("Brocade Port Discovery"),
            elements=[
                ("use_portname",
                 Checkbox(title=_("Use port name as service name"),
                          label=_("use port name"),
                          default_value=True,
                          help=_(
                              "This option lets Check_MK use the port name as item instead of the "
                              "port number. If no description is available then the port number is "
                              "used anyway."))),
                ("show_isl",
                 Checkbox(title=_("add \"ISL\" to service description for interswitch links"),
                          label=_("add ISL"),
                          default_value=True,
                          help=_("This option lets Check_MK add the string \"ISL\" to the service "
                                 "description for interswitch links."))),
                ("admstates",
                 ListChoice(
                     title=_("Administrative port states to discover"),
                     help=_(
                         "When doing service discovery on brocade switches only ports with the given administrative "
                         "states will be added to the monitoring system."),
                     choices=_brocade_fcport_adm_choices,
                     columns=1,
                     toggle_all=True,
                     default_value=['1', '3', '4'],
                 )),
                ("phystates",
                 ListChoice(
                     title=_("Physical port states to discover"),
                     help=_(
                         "When doing service discovery on brocade switches only ports with the given physical "
                         "states will be added to the monitoring system."),
                     choices=_brocade_fcport_phy_choices,
                     columns=1,
                     toggle_all=True,
                     default_value=[3, 4, 5, 6, 7, 8, 9, 10])),
                ("opstates",
                 ListChoice(
                     title=_("Operational port states to discover"),
                     help=_(
                         "When doing service discovery on brocade switches only ports with the given operational "
                         "states will be added to the monitoring system."),
                     choices=_brocade_fcport_op_choices,
                     columns=1,
                     toggle_all=True,
                     default_value=[1, 2, 3, 4])),
            ],
            help=_('This rule can be used to control the service discovery for brocade ports. '
                   'You can configure the port states for inventory '
                   'and the use of the description as service name.'),
        )


@rulespec_registry.register
class RulespecCheckgroupParametersBrocadeFcport(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "brocade_fcport"

    @property
    def title(self):
        return _("Brocade FibreChannel ports")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("bw",
             Alternative(
                 title=_("Throughput levels"),
                 help=_("Please note: in a few cases the automatic detection of the link speed "
                        "does not work. In these cases you have to set the link speed manually "
                        "below if you want to monitor percentage values"),
                 elements=[
                     Tuple(title=_("Used bandwidth of port relative to the link speed"),
                           elements=[
                               Percentage(title=_("Warning at"), unit=_("percent")),
                               Percentage(title=_("Critical at"), unit=_("percent")),
                           ]),
                     Tuple(title=_("Used Bandwidth of port in megabyte/s"),
                           elements=[
                               Integer(title=_("Warning at"), unit=_("MByte/s")),
                               Integer(title=_("Critical at"), unit=_("MByte/s")),
                           ])
                 ])),
            ("assumed_speed",
             Float(title=_("Assumed link speed"),
                   help=_("If the automatic detection of the link speed does "
                          "not work you can set the link speed here."),
                   unit=_("GByte/s"))),
            ("rxcrcs",
             Tuple(title=_("CRC errors rate"),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent")),
                       Percentage(title=_("Critical at"), unit=_("percent")),
                   ])),
            ("rxencoutframes",
             Tuple(title=_("Enc-Out frames rate"),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent")),
                       Percentage(title=_("Critical at"), unit=_("percent")),
                   ])),
            ("rxencinframes",
             Tuple(title=_("Enc-In frames rate"),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent")),
                       Percentage(title=_("Critical at"), unit=_("percent")),
                   ])),
            ("notxcredits",
             Tuple(title=_("No-TxCredits errors"),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent")),
                       Percentage(title=_("Critical at"), unit=_("percent")),
                   ])),
            ("c3discards",
             Tuple(title=_("C3 discards"),
                   elements=[
                       Percentage(title=_("Warning at"), unit=_("percent")),
                       Percentage(title=_("Critical at"), unit=_("percent")),
                   ])),
            ("average",
             Integer(
                 title=_("Averaging"),
                 help=_("If this parameter is set, all throughputs will be averaged "
                        "over the specified time interval before levels are being applied. Per "
                        "default, averaging is turned off. "),
                 unit=_("minutes"),
                 minvalue=1,
                 default_value=60,
             )),
            ("phystate",
             Optional(
                 ListChoice(title=_("Allowed states (otherwise check will be critical)"),
                            choices=[
                                (1, _("noCard")),
                                (2, _("noTransceiver")),
                                (3, _("laserFault")),
                                (4, _("noLight")),
                                (5, _("noSync")),
                                (6, _("inSync")),
                                (7, _("portFault")),
                                (8, _("diagFault")),
                                (9, _("lockRef")),
                            ]),
                 title=_("Physical state of port"),
                 negate=True,
                 label=_("ignore physical state"),
             )),
            ("opstate",
             Optional(
                 ListChoice(title=_("Allowed states (otherwise check will be critical)"),
                            choices=[
                                (0, _("unknown")),
                                (1, _("online")),
                                (2, _("offline")),
                                (3, _("testing")),
                                (4, _("faulty")),
                            ]),
                 title=_("Operational state"),
                 negate=True,
                 label=_("ignore operational state"),
             )),
            ("admstate",
             Optional(
                 ListChoice(title=_("Allowed states (otherwise check will be critical)"),
                            choices=[
                                (1, _("online")),
                                (2, _("offline")),
                                (3, _("testing")),
                                (4, _("faulty")),
                            ]),
                 title=_("Administrative state"),
                 negate=True,
                 label=_("ignore administrative state"),
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(
            title=_("port name"),
            help=_("The name of the switch port"),
        )
