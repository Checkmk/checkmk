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
    TextAscii,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    get_free_used_dynamic_valuespec,
    transform_filesystem_free,
)


def _item_spec_db2_logsize():
    return TextAscii(title=_("Instance"),
                     help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1"))


def _parameter_valuespec_db2_logsize():
    return Dictionary(elements=[("levels",
                                 Transform(get_free_used_dynamic_valuespec("free",
                                                                           "logfile",
                                                                           default_value=(20.0,
                                                                                          10.0)),
                                           title=_("Logfile levels"),
                                           allow_empty=False,
                                           forth=transform_filesystem_free,
                                           back=transform_filesystem_free))],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_logsize",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_logsize,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_logsize,
        title=lambda: _("DB2 logfile usage"),
    ))
