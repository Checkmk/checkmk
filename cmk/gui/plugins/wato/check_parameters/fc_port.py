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
    Dictionary,
    Float,
    Integer,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _item_spec_fc_port():
    return TextAscii(
        title=_("port name"),
        help=_("The name of the FC port"),
    )


def _parameter_valuespec_fc_port():
    return Dictionary(
        elements=[
            ("bw",
             Alternative(
                 title=_("Throughput levels"),
                 help=_("Please note: in a few cases the automatic detection of the link speed "
                        "does not work. In these cases you have to set the link speed manually "
                        "below if you want to monitor percentage values"),
                 elements=[
                     Tuple(
                         title=_("Used bandwidth of port relative to the link speed"),
                         elements=[
                             Percentage(title=_("Warning at"), unit=_("percent")),
                             Percentage(title=_("Critical at"), unit=_("percent")),
                         ],
                     ),
                     Tuple(
                         title=_("Used Bandwidth of port in megabyte/s"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_("MByte/s")),
                             Integer(title=_("Critical at"), unit=_("MByte/s")),
                         ],
                     )
                 ],
             )),
            ("assumed_speed",
             Float(title=_("Assumed link speed"),
                   help=_("If the automatic detection of the link speed does "
                          "not work you can set the link speed here."),
                   unit=_("Gbit/s"))),
            ("rxcrcs",
             Tuple(
                 title=_("CRC errors rate"),
                 elements=[
                     Percentage(title=_("Warning at"), unit=_("percent")),
                     Percentage(title=_("Critical at"), unit=_("percent")),
                 ],
             )),
            ("rxencoutframes",
             Tuple(
                 title=_("Enc-Out frames rate"),
                 elements=[
                     Percentage(title=_("Warning at"), unit=_("percent")),
                     Percentage(title=_("Critical at"), unit=_("percent")),
                 ],
             )),
            ("notxcredits",
             Tuple(
                 title=_("No-TxCredits errors"),
                 elements=[
                     Percentage(title=_("Warning at"), unit=_("percent")),
                     Percentage(title=_("Critical at"), unit=_("percent")),
                 ],
             )),
            ("c3discards",
             Tuple(
                 title=_("C3 discards"),
                 elements=[
                     Percentage(title=_("Warning at"), unit=_("percent")),
                     Percentage(title=_("Critical at"), unit=_("percent")),
                 ],
             )),
            ("average",
             Integer(
                 title=_("Averaging"),
                 help=_("If this parameter is set, all throughputs will be averaged "
                        "over the specified time interval before levels are being applied. Per "
                        "default, averaging is turned off. "),
                 unit=_("minutes"),
                 minvalue=1,
                 default_value=5,
             )),
            #("phystate",
            # Optional(
            #     ListChoice(
            #         title=_("Allowed states (otherwise check will be critical)"),
            #         choices=[
            #             (1, _("unknown")),
            #             (2, _("failed")),
            #             (3, _("bypassed")),
            #             (4, _("active")),
            #             (5, _("loopback")),
            #             (6, _("txfault")),
            #             (7, _("nomedia")),
            #             (8, _("linkdown")),
            #         ],),
            #     title=_("Physical state of port"),
            #     negate=True,
            #     label=_("ignore physical state"),
            # )),
            #("opstate",
            # Optional(
            #     ListChoice(
            #         title=_("Allowed states (otherwise check will be critical)"),
            #         choices=[
            #             (1, _("unknown")),
            #             (2, _("unused")),
            #             (3, _("ready")),
            #             (4, _("warning")),
            #             (5, _("failure")),
            #             (6, _("not participating")),
            #             (7, _("initializing")),
            #             (8, _("bypass")),
            #             (9, _("ols")),
            #         ],),
            #     title=_("Operational state"),
            #     negate=True,
            #     label=_("ignore operational state"),
            # )),
            #("admstate",
            # Optional(
            #     ListChoice(
            #         title=_("Allowed states (otherwise check will be critical)"),
            #         choices=[
            #             (1, _("unknown")),
            #             (2, _("online")),
            #             (3, _("offline")),
            #             (4, _("bypassed")),
            #             (5, _("diagnostics")),
            #         ],),
            #     title=_("Administrative state"),
            #     negate=True,
            #     label=_("ignore administrative state"),
            # ))
        ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fc_port",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_fc_port,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fc_port,
        title=lambda: _("FibreChannel Ports (FCMGMT MIB)"),
    ))
