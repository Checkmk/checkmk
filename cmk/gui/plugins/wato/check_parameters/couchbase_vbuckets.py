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
    Filesize,
    Percentage,
    Integer,
    TextAscii,
    Tuple,
    Dictionary,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_couchbase_vbuckets():
    return Dictionary(
        title=_("Couchbase vBuckets"),
        elements=[
            ("item_memory",
             Tuple(
                 title="Item memory size",
                 elements=[
                     Filesize(title=_("Warning at")),
                     Filesize(title=_("Critical at")),
                 ],
             )),
            ("resident_items_ratio",
             Tuple(
                 title="Active vBuckets: Lower levels for resident items ratio",
                 elements=[
                     Percentage(title=_("Warning at or below"), unit="%"),
                     Percentage(title=_("Critical at or below"), unit="%"),
                 ],
             )),
            ("vb_pending_num",
             Tuple(
                 title="Active vBuckets: Levels for number of pending vBuckets",
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
            ("vb_replica_num",
             Tuple(
                 title="Replica vBuckets: Levels for total number of replica vBuckets",
                 elements=[
                     Integer(title=_("Warning at")),
                     Integer(title=_("Critical at")),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_vbuckets",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Bucket name')),
        parameter_valuespec=_parameter_valuespec_couchbase_vbuckets,
        title=lambda: _("Couchbase vBuckets"),
    ))
