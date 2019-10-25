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
    TextAscii,
    Tuple,
    Dictionary,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _tuple(title):
    return Tuple(
        title=title,
        elements=[
            Filesize(title='Warning',),
            Filesize(title='Critical',),
        ],
    )


def _valuespec_couchbase_size(title):
    def _get_spec():
        return Dictionary(
            title=title,
            elements=[
                ('size_on_disk', _tuple(_('Levels for size on disk'))),
                ('size', _tuple(_('Levels for data size'))),
            ],
        )

    return _get_spec


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_size_docs",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Node name')),
        parameter_valuespec=_valuespec_couchbase_size(_("Couchbase Node: Size of documents")),
        title=lambda: _("Couchbase Node: Size of documents"),
    ))

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_size_spacial",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Node name')),
        parameter_valuespec=_valuespec_couchbase_size(_("Couchbase Node: Size of spacial views")),
        title=lambda: _("Couchbase Node: Size of spacial views"),
    ))

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_size_couch",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Node name')),
        parameter_valuespec=_valuespec_couchbase_size(_("Couchbase Node: Size of couch views")),
        title=lambda: _("Couchbase Node: Size of couch views"),
    ))
