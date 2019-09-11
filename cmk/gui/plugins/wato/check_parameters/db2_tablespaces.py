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
    Filesize,
    Float,
    Integer,
    ListOf,
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def db_levels_common():
    return [
        ("levels",
         Alternative(title=_("Levels for the Tablespace usage"),
                     default_value=(10.0, 5.0),
                     elements=[
                         Tuple(title=_("Percentage free space"),
                               elements=[
                                   Percentage(title=_("Warning if below"), unit=_("% free")),
                                   Percentage(title=_("Critical if below"), unit=_("% free")),
                               ]),
                         Tuple(title=_("Absolute free space"),
                               elements=[
                                   Integer(title=_("Warning if below"),
                                           unit=_("MB"),
                                           default_value=1000),
                                   Integer(title=_("Critical if below"),
                                           unit=_("MB"),
                                           default_value=500),
                               ]),
                         ListOf(
                             Tuple(
                                 orientation="horizontal",
                                 elements=[
                                     Filesize(title=_("Tablespace larger than")),
                                     Alternative(
                                         title=_("Levels for the Tablespace size"),
                                         elements=[
                                             Tuple(title=_("Percentage free space"),
                                                   elements=[
                                                       Percentage(title=_("Warning if below"),
                                                                  unit=_("% free")),
                                                       Percentage(title=_("Critical if below"),
                                                                  unit=_("% free")),
                                                   ]),
                                             Tuple(title=_("Absolute free space"),
                                                   elements=[
                                                       Integer(title=_("Warning if below"),
                                                               unit=_("MB")),
                                                       Integer(title=_("Critical if below"),
                                                               unit=_("MB")),
                                                   ]),
                                         ]),
                                 ],
                             ),
                             title=_('Dynamic levels'),
                         ),
                     ])),
        ("magic",
         Float(title=_("Magic factor (automatic level adaptation for large tablespaces)"),
               help=_("This is only be used in case of percentual levels"),
               minvalue=0.1,
               maxvalue=1.0,
               default_value=0.9)),
        ("magic_normsize",
         Integer(title=_("Reference size for magic factor"),
                 minvalue=1,
                 default_value=1000,
                 unit=_("MB"))),
        ("magic_maxlevels",
         Tuple(title=_("Maximum levels if using magic factor"),
               help=_("The tablespace levels will never be raise above these values, when using "
                      "the magic factor and the tablespace is very small."),
               elements=[
                   Percentage(title=_("Maximum warning level"),
                              unit=_("% free"),
                              allow_int=True,
                              default_value=60.0),
                   Percentage(title=_("Maximum critical level"),
                              unit=_("% free"),
                              allow_int=True,
                              default_value=50.0),
               ])),
    ]


def _item_spec_db2_tablespaces():
    return TextAscii(title=_("Instance"),
                     help=_("The instance name, the database name and the tablespace name combined "
                            "like this db2wps8:WPSCOMT8.USERSPACE1"))


def _parameter_valuespec_db2_tablespaces():
    return Dictionary(
        help=_("A tablespace is a container for segments (tables, indexes, etc). A "
               "database consists of one or more tablespaces, each made up of one or "
               "more data files. Tables and indexes are created within a particular "
               "tablespace. "
               "This rule allows you to define checks on the size of tablespaces."),
        elements=db_levels_common(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_tablespaces",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_tablespaces,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_tablespaces,
        title=lambda: _("DB2 Tablespaces"),
    ))
