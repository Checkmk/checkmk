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
    DropdownChoice,
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_domino_mailqueues():
    return DropdownChoice(
        choices=[
            ('lnDeadMail', _('Mails in Dead Queue')),
            ('lnWaitingMail', _('Mails in Waiting Queue')),
            ('lnMailHold', _('Mails in Hold Queue')),
            ('lnMailTotalPending', _('Total Pending Mails')),
            ('InMailWaitingforDNS', _('Mails Waiting for DNS Queue')),
        ],
        title=_("Domino Mail Queue Names"),
    )


def _parameter_valuespec_domino_mailqueues():
    return Dictionary(
        elements=[
            ("queue_length",
             Tuple(
                 title=_("Number of Mails in Queue"),
                 elements=[
                     Integer(title=_("warning at"), default_value=300),
                     Integer(title=_("critical at"), default_value=350),
                 ],
             )),
        ],
        required_keys=['queue_length'],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="domino_mailqueues",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_domino_mailqueues,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_domino_mailqueues,
        title=lambda: _("Lotus Domino Mail Queues"),
    ))
