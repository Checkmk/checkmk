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
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


@rulespec_registry.register
class RulespecCheckgroupParametersDdnS2APortErrors(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "ddn_s2a_port_errors"

    @property
    def title(self):
        return _("Port errors of DDN S2A devices")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("link_failure_errs",
             Tuple(
                 title=_(u"Link failure errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("lost_sync_errs",
             Tuple(
                 title=_(u"Lost synchronization errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("loss_of_signal_errs",
             Tuple(
                 title=_(u"Loss of signal errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("prim_seq_errs",
             Tuple(
                 title=_(u"PrimSeq erros"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("crc_errs",
             Tuple(
                 title=_(u"CRC errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("receive_errs",
             Tuple(
                 title=_(u"Receive errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("ctio_timeouts",
             Tuple(
                 title=_(u"CTIO timeouts"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("ctio_xmit_errs",
             Tuple(
                 title=_(u"CTIO transmission errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
            ("ctio_other_errs",
             Tuple(
                 title=_(u"other CTIO errors"),
                 elements=[
                     Integer(title=_(u"Warning at")),
                     Integer(title=_(u"Critical at")),
                 ],
             )),
        ],)

    @property
    def item_spec(self):
        return TextAscii(title="Port index")
