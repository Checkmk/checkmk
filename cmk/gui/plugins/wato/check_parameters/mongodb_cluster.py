#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at https://checkmk.com/.
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
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    RulespecGroupCheckParametersStorage,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, Integer, TextAscii, Tuple


@rulespec_registry.register
class RulespecCheckgroupParametersMongodbCollectionCluster(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "mongodb_cluster"

    @property
    def title(self):
        return _("MongoDB Cluster")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("levels_number_jumbo",
             self._count_tuple("Number of jumbo chunks per shard per collection", "above")),
        ])

    def _count_tuple(self, title, course):
        return Tuple(title=_(title),
                     elements=[
                         Integer(title=_("Warning if %s") % course, unit=_("count"), minvalue=0),
                         Integer(title=_("Critical if %s") % course, unit=_("count"), minvalue=0),
                     ])

    @property
    def item_spec(self):
        return TextAscii(title=_("Database/Collection name ('<DB name> <collection name>')"),)
