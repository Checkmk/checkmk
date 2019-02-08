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
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)

mailqueue_params = Dictionary(
    elements=[
        (
            "deferred",
            Tuple(
                title=_("Mails in outgoing mail queue/deferred mails"),
                help=_("This rule is applied to the number of E-Mails currently "
                       "in the deferred mail queue, or in the general outgoing mail "
                       "queue, if such a distinction is not available."),
                elements=[
                    Integer(title=_("Warning at"), unit=_("mails"), default_value=10),
                    Integer(title=_("Critical at"), unit=_("mails"), default_value=20),
                ],
            ),
        ),
        (
            "active",
            Tuple(
                title=_("Mails in active mail queue"),
                help=_("This rule is applied to the number of E-Mails currently "
                       "in the active mail queue"),
                elements=[
                    Integer(title=_("Warning at"), unit=_("mails"), default_value=800),
                    Integer(title=_("Critical at"), unit=_("mails"), default_value=1000),
                ],
            ),
        ),
    ],
    optional_keys=["active"],
)


@rulespec_registry.register
class RulespecCheckgroupParametersMailqueueLength(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "mailqueue_length"

    @property
    def title(self):
        return _("Number of mails in outgoing mail queue")

    @property
    def match_type(self):
        return "dict"

    @property
    def is_deprecated(self):
        return True

    @property
    def parameter_valuespec(self):
        return Transform(
            mailqueue_params,
            forth=lambda old: not isinstance(old, dict) and {"deferred": old} or old,
        )
