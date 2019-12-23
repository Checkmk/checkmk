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
    Integer,
    Float,
    TextAscii,
    Tuple,
    Dictionary,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _int_tuple(title):
    return Tuple(
        title=title,
        elements=[
            Integer(title='Warning',),
            Integer(title='Critical',),
        ],
    )


def _float_tuple(title):
    return Tuple(
        title=title,
        elements=[
            Float(title='Warning', unit='/s'),
            Float(title='Critical', unit='/s'),
        ],
    )


def _parameter_valuespec_couchbase_operations():
    return Dictionary(
        title=_('Couchbase Nodes: Items'),
        elements=[
            ('curr_items', _int_tuple(_('Levels for active items'))),
            ('non_residents', _int_tuple(_('Levels for non-resident items'))),
            ('curr_items_tot', _int_tuple(_('Levels for total number of items'))),
            ('fetched_items', _int_tuple(_('Buckets only: Levels for number of items fetched from disk'))),
            ('disk_write_ql', _int_tuple(_('Buckets only: Levels for length of disk write queue'))),
            ('disk_fill_rate', _float_tuple(_('Buckets only: Levels for disk queue fill rate'))),
            ('disk_drain_rate', _float_tuple(_('Buckets only: Levels for disk queue drain rate'))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_items",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Node or Bucket name')),
        parameter_valuespec=_parameter_valuespec_couchbase_operations,
        title=lambda: _("Couchbase Items"),
    ))
