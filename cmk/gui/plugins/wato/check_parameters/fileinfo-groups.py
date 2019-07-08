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
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
    HostRulespec,
)


@rulespec_registry.register
class RulespecFileinfoGroups(HostRulespec):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def name(self):
        return "fileinfo_groups"

    @property
    def match_type(self):
        return "all"

    @property
    def valuespec(self):
        return ListOf(
            Tuple(
                help=_("This defines one file grouping pattern."),
                show_titles=True,
                orientation="horizontal",
                elements=[
                    TextAscii(
                        title=_("Name of group"),
                        size=10,
                    ),
                    Transform(
                        Tuple(
                            show_titles=True,
                            orientation="vertical",
                            elements=[
                                TextAscii(title=_("Include Pattern"), size=40),
                                TextAscii(title=_("Exclude Pattern"), size=40),
                            ],
                        ),
                        forth=lambda params: isinstance(params, str) and (params, '') or params),
                ],
            ),
            title=_('File Grouping Patterns'),
            help=_('The check <tt>fileinfo</tt> monitors the age and size of '
                   'a single file. Each file information that is sent '
                   'by the agent will create one service. By defining grouping '
                   'patterns you can switch to the check <tt>fileinfo.groups</tt>. '
                   'That check monitors a list of files at once. You can set levels '
                   'not only for the total size and the age of the oldest/youngest '
                   'file but also on the count. You can define one or several '
                   'patterns for a group containing <tt>*</tt> and <tt>?</tt>, for example '
                   '<tt>/var/log/apache/*.log</tt>. Please see Python\'s fnmatch for more '
                   'information regarding globbing patterns and special characters. '
                   'If the pattern begins with a tilde then this pattern is interpreted as '
                   'a regular expression instead of as a filename globbing pattern and '
                   '<tt>*</tt> and <tt>?</tt> are treated differently. '
                   'For files contained in a group '
                   'the discovery will automatically create a group service instead '
                   'of single services for each file. This rule also applies when '
                   'you use manually configured checks instead of inventorized ones. '
                   'Furthermore, the current time/date in a configurable format '
                   'may be included in the include pattern. The syntax is as follows: '
                   '$DATE:format-spec$ or $YESTERDAY:format-spec$, where format-spec '
                   'is a list of time format directives of the unix date command. '
                   'Example: $DATE:%Y%m%d$ is todays date, e.g. 20140127. A pattern '
                   'of /var/tmp/backups/$DATE:%Y%m%d$.txt would search for .txt files '
                   'with todays date  as name in the directory /var/tmp/backups. '
                   'The YESTERDAY syntax simply subtracts one day from the reference time.'),
            add_label=_("Add pattern group"),
        )


@rulespec_registry.register
class RulespecCheckgroupParametersFileinfoGroups(CheckParameterRulespecWithItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersStorage

    @property
    def check_group_name(self):
        return "fileinfo-groups"

    @property
    def title(self):
        return _("Size, age and count of file groups")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                ("minage_oldest",
                 Tuple(
                     title=_("Minimal age of oldest file"),
                     elements=[
                         Age(title=_("Warning if younger than")),
                         Age(title=_("Critical if younger than")),
                     ],
                 )),
                ("maxage_oldest",
                 Tuple(
                     title=_("Maximal age of oldest file"),
                     elements=[
                         Age(title=_("Warning if older than")),
                         Age(title=_("Critical if older than")),
                     ],
                 )),
                ("minage_newest",
                 Tuple(
                     title=_("Minimal age of newest file"),
                     elements=[
                         Age(title=_("Warning if younger than")),
                         Age(title=_("Critical if younger than")),
                     ],
                 )),
                ("maxage_newest",
                 Tuple(
                     title=_("Maximal age of newest file"),
                     elements=[
                         Age(title=_("Warning if older than")),
                         Age(title=_("Critical if older than")),
                     ],
                 )),
                ("minsize_smallest",
                 Tuple(
                     title=_("Minimal size of smallest file"),
                     elements=[
                         Filesize(title=_("Warning if below")),
                         Filesize(title=_("Critical if below")),
                     ],
                 )),
                ("maxsize_smallest",
                 Tuple(
                     title=_("Maximal size of smallest file"),
                     elements=[
                         Filesize(title=_("Warning if above")),
                         Filesize(title=_("Critical if above")),
                     ],
                 )),
                ("minsize_largest",
                 Tuple(
                     title=_("Minimal size of largest file"),
                     elements=[
                         Filesize(title=_("Warning if below")),
                         Filesize(title=_("Critical if below")),
                     ],
                 )),
                ("maxsize_largest",
                 Tuple(
                     title=_("Maximal size of largest file"),
                     elements=[
                         Filesize(title=_("Warning if above")),
                         Filesize(title=_("Critical if above")),
                     ],
                 )),
                ("minsize",
                 Tuple(
                     title=_("Minimal size"),
                     elements=[
                         Filesize(title=_("Warning if below")),
                         Filesize(title=_("Critical if below")),
                     ],
                 )),
                ("maxsize",
                 Tuple(
                     title=_("Maximal size"),
                     elements=[
                         Filesize(title=_("Warning if above")),
                         Filesize(title=_("Critical if above")),
                     ],
                 )),
                ("mincount",
                 Tuple(
                     title=_("Minimal file count"),
                     elements=[
                         Integer(title=_("Warning if below")),
                         Integer(title=_("Critical if below")),
                     ],
                 )),
                ("maxcount",
                 Tuple(
                     title=_("Maximal file count"),
                     elements=[
                         Integer(title=_("Warning if above")),
                         Integer(title=_("Critical if above")),
                     ],
                 )),
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
                                     ("largest_size_lower", _("Largest file size below"),
                                      Filesize()),
                                     ("smallest_size", _("Smallest file size at"), Filesize()),
                                     ("smallest_size_lower", _("Smallest file size below"),
                                      Filesize()),
                                     ("oldest_age", _("Oldest file age at"), Age()),
                                     ("oldest_age_lower", _("Oldest file age below"), Age()),
                                     ("newest_age", _("Newest file age at"), Age()),
                                     ("newest_age_lower", _("Newest file age below"), Age()),
                                 ],
                             ),
                             magic="@#@#",
                         )
                     ],),
                     title=_("Level conjunctions"),
                     help=
                     _("In order to check dependent file group statistics you can configure "
                       "conjunctions of single levels now. A conjunction consists of a monitoring state "
                       "and any number of upper or lower levels. If all of the configured levels within "
                       "a conjunction are reached then the related state is reported."),
                 )),
            ],
            ignored_keys=["precompiled_patterns"],
        )

    @property
    def item_spec(self):
        return TextAscii(
            title=_("File Group Name"),
            help=
            _("This name must match the name of the group defined "
              "in the <a href=\"wato.py?mode=edit_ruleset&varname=fileinfo_groups\">%s</a> ruleset."
             ) % (_('File Grouping Patterns')),
            allow_empty=True)
