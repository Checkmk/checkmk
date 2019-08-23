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
    Dictionary,
    Integer,
    ListOf,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    ABCHostValueRulespec,
)


def transform_msx_queues(params):
    if isinstance(params, tuple):
        return {"levels": (params[0], params[1])}
    return params


@rulespec_registry.register
class RulespecWinperfMsxQueuesInventory(ABCHostValueRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersDiscovery

    @property
    def name(self):
        return "winperf_msx_queues_inventory"

    @property
    def match_type(self):
        return "all"

    @property
    def valuespec(self):
        return ListOf(
            Tuple(orientation="horizontal",
                  elements=[
                      TextAscii(
                          title=_("Name of Counter"),
                          help=_("Name of the Counter to be monitored."),
                          size=50,
                          allow_empty=False,
                      ),
                      Integer(
                          title=_("Offset"),
                          help=_("The offset of the information relative to counter base"),
                          allow_empty=False,
                      ),
                  ]),
            title=_('MS Exchange Message Queues Discovery'),
            help=
            _('Per default the offsets of all Windows performance counters are preconfigured in the check. '
              'If the format of your counters object is not compatible then you can adapt the counter '
              'offsets manually.'),
            movable=False,
            add_label=_("Add Counter"),
        )


@rulespec_registry.register
class RulespecCheckgroupParametersMsxQueues(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "msx_queues"

    @property
    def title(self):
        return _("MS Exchange Message Queues")

    @property
    def parameter_valuespec(self):
        return Transform(
            Dictionary(
                title=_("Set Levels"),
                elements=[
                    ('levels',
                     Tuple(
                         title=_("Maximum Number of E-Mails in Queue"),
                         elements=[
                             Integer(title=_("Warning at"), unit=_("E-Mails")),
                             Integer(title=_("Critical at"), unit=_("E-Mails"))
                         ],
                     )),
                    ('offset',
                     Integer(
                         title=_("Offset"),
                         help=
                         _("Use this only if you want to overwrite the postion of the information in the agent "
                           "output. Also refer to the rule <i>Microsoft Exchange Queues Discovery</i> "
                          ))),
                ],
                optional_keys=["offset"],
            ),
            forth=transform_msx_queues,
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("Explicit Queue Names"),
            help=_("Specify queue names that the rule should apply to"),
        )
