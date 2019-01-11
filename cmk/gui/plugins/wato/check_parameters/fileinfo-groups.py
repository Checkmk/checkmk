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
    Age,
    CascadingDropdown,
    Dictionary,
    Filesize,
    Integer,
    ListOf,
    ListOfTimeRanges,
    MonitoringState,
    TextAscii,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersStorage,
    "fileinfo-groups",
    _("Size, age and count of file groups"),
    Dictionary(
        elements=[
            ("minage_oldest",
             Tuple(
                 title=_("Minimal age of oldest file"),
                 elements=[
                     Age(title=_("Warning if younger than")),
                     Age(title=_("Critical if younger than")),
                 ])),
            ("maxage_oldest",
             Tuple(
                 title=_("Maximal age of oldest file"),
                 elements=[
                     Age(title=_("Warning if older than")),
                     Age(title=_("Critical if older than")),
                 ])),
            ("minage_newest",
             Tuple(
                 title=_("Minimal age of newest file"),
                 elements=[
                     Age(title=_("Warning if younger than")),
                     Age(title=_("Critical if younger than")),
                 ])),
            ("maxage_newest",
             Tuple(
                 title=_("Maximal age of newest file"),
                 elements=[
                     Age(title=_("Warning if older than")),
                     Age(title=_("Critical if older than")),
                 ])),
            ("minsize_smallest",
             Tuple(
                 title=_("Minimal size of smallest file"),
                 elements=[
                     Filesize(title=_("Warning if below")),
                     Filesize(title=_("Critical if below")),
                 ])),
            ("maxsize_smallest",
             Tuple(
                 title=_("Maximal size of smallest file"),
                 elements=[
                     Filesize(title=_("Warning if above")),
                     Filesize(title=_("Critical if above")),
                 ])),
            ("minsize_largest",
             Tuple(
                 title=_("Minimal size of largest file"),
                 elements=[
                     Filesize(title=_("Warning if below")),
                     Filesize(title=_("Critical if below")),
                 ])),
            ("maxsize_largest",
             Tuple(
                 title=_("Maximal size of largest file"),
                 elements=[
                     Filesize(title=_("Warning if above")),
                     Filesize(title=_("Critical if above")),
                 ])),
            ("minsize",
             Tuple(
                 title=_("Minimal size"),
                 elements=[
                     Filesize(title=_("Warning if below")),
                     Filesize(title=_("Critical if below")),
                 ])),
            ("maxsize",
             Tuple(
                 title=_("Maximal size"),
                 elements=[
                     Filesize(title=_("Warning if above")),
                     Filesize(title=_("Critical if above")),
                 ])),
            ("mincount",
             Tuple(
                 title=_("Minimal file count"),
                 elements=[
                     Integer(title=_("Warning if below")),
                     Integer(title=_("Critical if below")),
                 ])),
            ("maxcount",
             Tuple(
                 title=_("Maximal file count"),
                 elements=[
                     Integer(title=_("Warning if above")),
                     Integer(title=_("Critical if above")),
                 ])),
            ("timeofday",
             ListOfTimeRanges(
                 title=_("Only check during the following times of the day"),
                 help=_("Outside these ranges the check will always be OK"),
             )),
            ("conjunctions",
             ListOf(
                 Tuple(elements=[
                     MonitoringState(title=_("Monitoring state"), default_value=2),
                     ListOf(
                         CascadingDropdown(
                             orientation="hroizontal",
                             choices=[
                                 ("count", _("File count at"), Integer()),
                                 ("count_lower", _("File count below"), Integer()),
                                 ("size", _("File size at"), Filesize()),
                                 ("size_lower", _("File size below"), Filesize()),
                                 ("largest_size", _("Largest file size at"), Filesize()),
                                 ("largest_size_lower", _("Largest file size below"), Filesize()),
                                 ("smallest_size", _("Smallest file size at"), Filesize()),
                                 ("smallest_size_lower", _("Smallest file size below"), Filesize()),
                                 ("oldest_age", _("Oldest file age at"), Age()),
                                 ("oldest_age_lower", _("Oldest file age below"), Age()),
                                 ("newest_age", _("Newest file age at"), Age()),
                                 ("newest_age_lower", _("Newest file age below"), Age()),
                             ]),
                         magic="@#@#",
                     )
                 ]),
                 title=_("Level conjunctions"),
                 help=
                 _("In order to check dependent file group statistics you can configure "
                   "conjunctions of single levels now. A conjunction consists of a monitoring state "
                   "and any number of upper or lower levels. If all of the configured levels within "
                   "a conjunction are reached then the related state is reported."),
             )),
        ],
        ignored_keys=["precompiled_patterns"]),
    TextAscii(
        title=_("File Group Name"),
        help=_(
            "This name must match the name of the group defined "
            "in the <a href=\"wato.py?mode=edit_ruleset&varname=fileinfo_groups\">%s</a> ruleset.")
        % (_('File Grouping Patterns')),
        allow_empty=True),
    match_type="dict",
)
