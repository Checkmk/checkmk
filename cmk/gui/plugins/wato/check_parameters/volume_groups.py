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
    TextAscii,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    get_free_used_dynamic_valuespec,
    match_dual_level_type,
    transform_filesystem_free,
)


@rulespec_registry.register
class RulespecCheckgroupParametersVolumeGroups(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "volume_groups"

    @property
    def title(self):
        return _("Volume Groups (LVM)")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(elements=[
            ("levels",
             Alternative(
                 title=_("Levels for volume group"),
                 show_alternative_title=True,
                 default_value=(80.0, 90.0),
                 match=match_dual_level_type,
                 elements=[
                     get_free_used_dynamic_valuespec("used", "volume group"),
                     Transform(get_free_used_dynamic_valuespec("free",
                                                               "volume group",
                                                               default_value=(20.0, 10.0)),
                               title=_("Levels for volume group free space"),
                               allow_empty=False,
                               forth=transform_filesystem_free,
                               back=transform_filesystem_free)
                 ],
             )),
        ],
                          optional_keys=False)

    @property
    def item_spec(self):
        return TextAscii(title=_("Volume Group"), allow_empty=False)
